#!/usr/bin/env python
"""
MSNBC Transcript Scraper using WordPress REST API.

Fetches all transcripts from https://www.msnow.ms/wp-json/wp/v2/transcript
and saves raw HTML content as gzipped files with structured metadata CSV.
"""

import csv
import gzip
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("msnbc_api_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.ms.now/wp-json/wp/v2"
TRANSCRIPT_ENDPOINT = f"{BASE_URL}/transcript"
SHOW_ENDPOINT = f"{BASE_URL}/show"
PER_PAGE = 100
REQUESTS_PER_MINUTE = 60
REQUEST_DELAY = 60.0 / REQUESTS_PER_MINUTE

DATA_DIR = Path(__file__).parent.parent / "data"
HTML_DIR = DATA_DIR / "html"
METADATA_FILE = DATA_DIR / "metadata.csv"
SHOWS_FILE = DATA_DIR / "shows.csv"
STATE_FILE = DATA_DIR / "scraper_state.json"

METADATA_COLUMNS = [
    "id",
    "date",
    "title",
    "url",
    "slug",
    "guests",
    "show_ids",
    "modified",
]


def create_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": "MSNBC-Transcript-Archiver/1.0 (Research Project)",
            "Accept": "application/json",
        }
    )
    return session


def load_state():
    """Load scraper state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_page": 0, "total_fetched": 0, "completed": False}


def save_state(state):
    """Save scraper state to file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_shows(session):
    """Fetch all shows from the taxonomy endpoint."""
    logger.info("Fetching shows taxonomy...")
    shows = []
    page = 1

    while True:
        params = {"per_page": 100, "page": page}
        try:
            resp = session.get(SHOW_ENDPOINT, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            shows.extend(data)
            logger.info(f"Fetched {len(data)} shows from page {page}")
            page += 1
            time.sleep(REQUEST_DELAY)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                break
            raise

    return shows


def save_shows(shows):
    """Save shows to CSV."""
    with open(SHOWS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "slug", "count"])
        writer.writeheader()
        for show in shows:
            writer.writerow(
                {
                    "id": show.get("id"),
                    "name": show.get("name", ""),
                    "slug": show.get("slug", ""),
                    "count": show.get("count", 0),
                }
            )
    logger.info(f"Saved {len(shows)} shows to {SHOWS_FILE}")


def get_total_pages(session):
    """Get total number of pages from API headers."""
    resp = session.get(
        TRANSCRIPT_ENDPOINT, params={"per_page": PER_PAGE, "page": 1}, timeout=30
    )
    resp.raise_for_status()
    total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
    total_items = int(resp.headers.get("X-WP-Total", 0))
    logger.info(f"Total transcripts: {total_items}, Total pages: {total_pages}")
    return total_pages, total_items, resp.json()


def extract_metadata(post):
    """Extract metadata from a WordPress post."""
    meta = post.get("meta", {})
    guests = meta.get("dek", "") if isinstance(meta, dict) else ""
    show_ids = post.get("show", [])
    if isinstance(show_ids, list):
        show_ids = ",".join(str(s) for s in show_ids)
    else:
        show_ids = str(show_ids) if show_ids else ""

    title_obj = post.get("title", {})
    title = title_obj.get("rendered", "") if isinstance(title_obj, dict) else str(title_obj)

    return {
        "id": post.get("id"),
        "date": post.get("date", ""),
        "title": title,
        "url": post.get("link", ""),
        "slug": post.get("slug", ""),
        "guests": guests,
        "show_ids": show_ids,
        "modified": post.get("modified", ""),
    }


def save_html(post_id, content):
    """Save HTML content as gzipped file."""
    filepath = HTML_DIR / f"{post_id}.html.gz"
    with gzip.open(filepath, "wt", encoding="utf-8") as f:
        f.write(content)


def fetch_transcripts(session, start_page=1):
    """Fetch all transcripts from the API."""
    state = load_state()
    if state.get("completed"):
        logger.info("Scraping already completed. Delete state file to restart.")
        return

    resume_page = max(start_page, state.get("last_page", 0) + 1)

    total_pages, total_items, first_page_data = get_total_pages(session)

    existing_ids = set()
    if METADATA_FILE.exists():
        with open(METADATA_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_ids = {row["id"] for row in reader}
        logger.info(f"Found {len(existing_ids)} existing transcripts in metadata")

    write_header = not METADATA_FILE.exists() or os.path.getsize(METADATA_FILE) == 0

    with open(METADATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=METADATA_COLUMNS)
        if write_header:
            writer.writeheader()

        page = resume_page
        fetched_count = state.get("total_fetched", 0)

        while page <= total_pages:
            logger.info(f"Fetching page {page}/{total_pages}")

            try:
                if page == 1 and first_page_data:
                    posts = first_page_data
                else:
                    params = {"per_page": PER_PAGE, "page": page}
                    resp = session.get(TRANSCRIPT_ENDPOINT, params=params, timeout=30)
                    resp.raise_for_status()
                    posts = resp.json()

                if not posts:
                    logger.info(f"No posts on page {page}, stopping")
                    break

                for post in posts:
                    post_id = str(post.get("id"))
                    if post_id in existing_ids:
                        continue

                    content_obj = post.get("content", {})
                    content = (
                        content_obj.get("rendered", "")
                        if isinstance(content_obj, dict)
                        else str(content_obj)
                    )
                    save_html(post_id, content)

                    metadata = extract_metadata(post)
                    writer.writerow(metadata)
                    f.flush()

                    fetched_count += 1
                    existing_ids.add(post_id)

                logger.info(
                    f"Page {page}: processed {len(posts)} posts, total: {fetched_count}"
                )

                state["last_page"] = page
                state["total_fetched"] = fetched_count
                save_state(state)

                page += 1
                time.sleep(REQUEST_DELAY)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page}: {e}")
                logger.info("Will retry after delay...")
                time.sleep(30)
                continue
            except KeyboardInterrupt:
                logger.info("Interrupted by user. State saved.")
                save_state(state)
                sys.exit(0)

    state["completed"] = True
    save_state(state)
    logger.info(f"Scraping complete. Total transcripts: {fetched_count}")


def verify_results():
    """Verify the scraping results."""
    html_files = list(HTML_DIR.glob("*.html.gz"))
    html_count = len(html_files)

    csv_count = 0
    if METADATA_FILE.exists():
        with open(METADATA_FILE, encoding="utf-8") as f:
            csv_count = sum(1 for _ in f) - 1

    logger.info(f"HTML files: {html_count}")
    logger.info(f"CSV rows: {csv_count}")

    if html_count != csv_count:
        logger.warning(f"Mismatch: {html_count} HTML files vs {csv_count} CSV rows")
    else:
        logger.info("HTML files and CSV rows match")

    if html_files:
        sample_file = html_files[0]
        with gzip.open(sample_file, "rt", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"Sample file {sample_file.name}: {len(content)} chars")
            if content.strip():
                logger.info("Sample content preview:")
                logger.info(content[:500])

    if METADATA_FILE.exists():
        with open(METADATA_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            dates = []
            for row in reader:
                if row.get("date"):
                    dates.append(row["date"][:10])
            if dates:
                dates.sort()
                logger.info(f"Date range: {dates[0]} to {dates[-1]}")


def main():
    """Main entry point."""
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    session = create_session()

    if not SHOWS_FILE.exists():
        shows = fetch_shows(session)
        save_shows(shows)

    fetch_transcripts(session)

    verify_results()


if __name__ == "__main__":
    main()
