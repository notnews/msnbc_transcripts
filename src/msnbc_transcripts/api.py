"""Fetch transcripts from the ms.now WordPress REST API into a JSONL checkpoint.

ms.now (MSNBC's domain since 2025) exposes transcripts as a custom post type at
``/wp-json/wp/v2/transcript``. Pages are 100 posts, newest first, and the
``X-WP-TotalPages`` header says how many there are. Because new posts shift
every page offset, resume is by the set of ids already in the checkpoint
rather than by page number.
"""

from __future__ import annotations

import gzip
import json
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from msnbc_transcripts import __version__
from msnbc_transcripts.checkpoint import prepare_checkpoint
from msnbc_transcripts.parsers import parse_api_post

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

log = logging.getLogger(__name__)

BASE_URL = "https://www.ms.now/wp-json/wp/v2"
TRANSCRIPTS = f"{BASE_URL}/transcript"
SHOWS = f"{BASE_URL}/show"
PER_PAGE = 100


@dataclass(slots=True)
class ScrapeSummary:
    """Counts reported at the end of a run."""

    pages: int = 0
    seen: int = 0
    written: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)


def make_session(timeout: float = 30.0, retries: int = 5) -> requests.Session:
    """Build a session that retries on 429 and 5xx with exponential backoff.

    Args:
        timeout: Seconds per request; applied by :func:`get`.
        retries: Total retry attempts per request.

    Returns:
        A configured ``requests.Session`` with the timeout stored on it.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "User-Agent": (
                f"msnbc-transcripts/{__version__} "
                "(+https://github.com/notnews/msnbc_transcripts)"
            ),
            "Accept": "application/json",
        }
    )
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def get(session: requests.Session, url: str, **params: Any) -> requests.Response:
    """GET with the session's timeout and raise on HTTP errors."""
    timeout = getattr(session, "request_timeout", 30.0)
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response


def load_seen_ids(path: Path) -> set[str]:
    """Return the ids already present in a JSONL checkpoint."""
    if not path.exists():
        return set()
    prepare_checkpoint(path)
    with path.open(encoding="utf-8") as handle:
        return {str(json.loads(line)["id"]) for line in handle if line.strip()}


def resolve_shows(session: requests.Session, post_id: str) -> list[str]:
    """Return show names attached to a post via the ``show`` taxonomy."""
    response = get(session, SHOWS, post=post_id, per_page=100)
    return [term["name"] for term in response.json()]


def scrape(
    out: Path,
    html_dir: Path,
    *,
    since: datetime | None = None,
    limit: int | None = None,
    requests_per_minute: int = 60,
    session: requests.Session | None = None,
) -> ScrapeSummary:
    """Append every transcript not yet in ``out`` and save its raw HTML.

    Args:
        out: JSONL checkpoint, one parsed transcript per line.
        html_dir: Where ``{id}.html.gz`` copies of ``content.rendered`` go, the
            format the published corpus uses.
        since: Only posts published after this timestamp (WordPress ``after``).
        limit: Stop after writing this many new transcripts.
        requests_per_minute: Politeness cap.
        session: Injected for tests; built by :func:`make_session` otherwise.

    Returns:
        Counts, including ids whose fetch or parse failed.
    """
    session = session or make_session()
    seen = load_seen_ids(out)
    summary = ScrapeSummary()
    delay = 60.0 / requests_per_minute
    if seen:
        log.info("resuming: %d transcripts already in %s", len(seen), out)
    out.parent.mkdir(parents=True, exist_ok=True)
    html_dir.mkdir(parents=True, exist_ok=True)

    params: dict[str, Any] = {"per_page": PER_PAGE, "page": 1}
    if since:
        params["after"] = since.isoformat()
    with out.open("a", encoding="utf-8") as handle:
        total_pages = 1
        while params["page"] <= total_pages:
            response = get(session, TRANSCRIPTS, **params)
            total_pages = int(response.headers.get("X-WP-TotalPages", 1))
            summary.pages += 1
            for post in response.json():
                summary.seen += 1
                post_id = str(post["id"])
                if post_id in seen:
                    summary.skipped += 1
                    continue
                try:
                    transcript = parse_api_post(post)
                    record = transcript.to_record()
                    record["shows"] = None
                    if transcript.show_ids:
                        record["shows"] = resolve_shows(session, post_id)
                        time.sleep(delay)
                    target = html_dir / f"{post_id}.html.gz"
                    part = target.with_suffix(".gz.part")
                    with gzip.open(part, "wt", encoding="utf-8") as raw:
                        raw.write(post["content"]["rendered"])
                    part.replace(target)
                except (requests.RequestException, KeyError, ValueError, OSError):
                    log.exception("failed: %s", post_id)
                    summary.failed.append(post_id)
                    continue
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                seen.add(post_id)
                summary.written += 1
                if limit is not None and summary.written >= limit:
                    _log_summary(summary)
                    return summary
            log.info(
                "page %d/%d: %d written", params["page"], total_pages, summary.written
            )
            params["page"] += 1
            time.sleep(delay)
    _log_summary(summary)
    return summary


def _log_summary(summary: ScrapeSummary) -> None:
    log.info(
        "done: %d pages, %d posts seen, %d written, %d skipped, %d failed",
        summary.pages,
        summary.seen,
        summary.written,
        summary.skipped,
        len(summary.failed),
    )
    for post_id in summary.failed:
        log.warning("failed: %s", post_id)
