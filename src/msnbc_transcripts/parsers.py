"""Parsers for the three sources the corpus was built from.

* ``parse_api_post``: a post from the ms.now WordPress REST API
  (``/wp-json/wp/v2/transcript``), the source of the 2010--2022 corpus.
* ``parse_rendered_html``: the ``content.rendered`` HTML of such a post, which
  carries a "Summary" and a "Transcript" heading followed by paragraphs.
* ``parse_legacy_page``: an nbcnews.com transcript page from 2008--2014
  (``<h1 class="entry-title">``, ``<abbr class="dtstamp">``, ``div#intelliTXT``).
"""

from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag
from dateutil import parser as dateparser

# API titles come in three shapes; the program name is the only stable part.
#   "Transcript: The 11th Hour with Stephanie Ruhle, 10/4/22"
#   "President Trump TRANSCRIPT: 8/7/20, The 11th Hour w/ Brian Williams"
#   "The Last Word with Lawrence O'Donnell, 7/19/22"
API_TITLE_PREFIXED = re.compile(
    r"^Transcript:\s*(?P<program>.+?)(?:,\s*[\d/]+)?\s*$", re.IGNORECASE
)
API_TITLE_INFIX = re.compile(r"TRANSCRIPT:\s*(?:[\d/]+,?\s*)?(?P<program>.+?)\.?\s*$")
API_TITLE_DATED = re.compile(r"^(?P<program>.+?),\s*[\d/]+\s*$")
DATE_TOKEN = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
# "'The Rachel Maddow Show' for Monday, August 30th, 2010"
LEGACY_TITLE = re.compile(r"^'?(?P<program>.+?)'?\s+for\s+(?P<date>.+)$", re.DOTALL)
GUESTS_PREFIX = re.compile(r"^Guests?:\s*", re.IGNORECASE)
# Legacy pages end with a copyright block ("<Copy: Content and programming
# copyright 2010 MSNBC ...", then "Copyright 2010 Roll Call, Inc. ..."), a
# template placeholder, and a "WATCH ... ON MSNBC." promo. Everything from the
# first of these paragraphs on is boilerplate. html.parser swallows the
# "<Copy:" paragraph as a malformed tag, so the Roll Call line is what we see.
LEGACY_TAIL = re.compile(
    r"^(?:<?Copy:|Copyright\s+\d{4}|PASTE THE TRANSCRIPT|END\s*$)", re.IGNORECASE
)
DAY_NAMES = re.compile(
    r"^(?:mon|tues?|wed(?:nes)?|thu(?:rs)?|fri|sat(?:ur)?|sun)[a-z]*day,?\s+",
    re.IGNORECASE,
)


@dataclass(slots=True)
class Transcript:
    """One transcript, whichever source it came from."""

    id: str
    url: str
    title: str | None
    program: str | None
    aired_date: date | None
    aired_time: str | None
    guests: str | None
    summary: str | None
    text: str
    wordcount: int
    show_ids: list[int]
    source: str

    def to_record(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict with ISO dates."""
        record = asdict(self)
        record["aired_date"] = self.aired_date.isoformat() if self.aired_date else None
        return record


def normalize_space(text: str) -> str:
    """Collapse whitespace runs, including non-breaking spaces, to one space."""
    return " ".join(html.unescape(text).split())


def _paragraphs(container: Tag) -> list[str]:
    lines = [normalize_space(p.get_text(" ")) for p in container.find_all("p")]
    return [line for line in lines if line]


def parse_rendered_html(rendered: str) -> tuple[str | None, str]:
    """Split a post's rendered HTML into (summary, transcript text).

    Args:
        rendered: ``content.rendered`` from the API.

    Returns:
        The summary paragraphs joined by newlines (``None`` when absent) and the
        transcript paragraphs joined by newlines (empty string when absent).
        Paragraphs before the first heading count as transcript text, so a post
        with no headings still yields its body.
    """
    soup = BeautifulSoup(rendered, "html.parser")
    sections: dict[str, list[str]] = {"summary": [], "transcript": []}
    current = "transcript"
    for node in soup.find_all(["h2", "h3", "p"]):
        if node.name in {"h2", "h3"}:
            heading = normalize_space(node.get_text()).lower()
            current = "summary" if heading.startswith("summary") else "transcript"
            continue
        line = normalize_space(node.get_text(" "))
        if line:
            sections[current].append(line)
    summary = "\n".join(sections["summary"]) or None
    return summary, "\n".join(sections["transcript"])


def _guests(description: str | None) -> str | None:
    if not description:
        return None
    text = normalize_space(description)
    if not GUESTS_PREFIX.match(text):
        return None
    guests = GUESTS_PREFIX.sub("", text).strip(" ,")
    return guests or None


def _program_from_api_title(title: str | None) -> str | None:
    """Best-effort program name from a title; ``None`` when no shape matches."""
    if not title:
        return None
    for pattern in (API_TITLE_PREFIXED, API_TITLE_INFIX, API_TITLE_DATED):
        match = pattern.search(title)
        if match:
            program = DATE_TOKEN.sub("", match["program"])
            program = re.sub(r",?\s*Transcript$", "", program, flags=re.IGNORECASE)
            program = program.replace(" w/ ", " with ").strip(" ,.")
            return program or None
    return None


def parse_api_post(post: dict[str, Any]) -> Transcript:
    """Parse one WordPress post object into a :class:`Transcript`.

    Args:
        post: A JSON object from ``/wp-json/wp/v2/transcript``.

    Returns:
        The transcript. ``guests`` comes from the SEO description because the
        ``meta`` block no longer carries a ``dek`` field; ``show_ids`` is the
        ``show`` taxonomy list, which the API returns empty for every post seen
        so far.
    """
    title = post.get("title")
    title_text = normalize_space(title["rendered"]) if isinstance(title, dict) else None
    content = post.get("content")
    rendered = content.get("rendered", "") if isinstance(content, dict) else ""
    summary, text = parse_rendered_html(rendered)
    when = post.get("date") or ""
    aired = datetime.fromisoformat(when) if when else None
    yoast = post.get("yoast_head_json") or {}
    shows = post.get("show") or []
    return Transcript(
        id=str(post["id"]),
        url=post.get("link", ""),
        title=title_text or None,
        program=_program_from_api_title(title_text),
        aired_date=aired.date() if aired else None,
        aired_time=aired.strftime("%H:%M") if aired else None,
        guests=_guests(yoast.get("description")),
        summary=summary,
        text=text,
        wordcount=len(text.split()),
        show_ids=[int(s) for s in shows],
        source="api",
    )


def parse_legacy_date(text: str) -> date | None:
    """Parse the free-text date of a legacy title, tolerating typos.

    The pages print the weekday, which is where the typos live
    ("Thusday", "Otcober" appears in month names too), so the weekday is
    stripped and the remainder is parsed fuzzily.
    """
    cleaned = DAY_NAMES.sub("", normalize_space(text))
    for typo, month in {"Februrary": "February", "Otcober": "October"}.items():
        cleaned = cleaned.replace(typo, month)
    if not re.search(r"\b(?:19|20)\d{2}\b", cleaned):
        return None
    try:
        return dateparser.parse(cleaned, fuzzy=True).date()
    except (ValueError, OverflowError):
        return None


def parse_legacy_page(page: str, url: str) -> Transcript:
    """Parse a 2008--2014 nbcnews.com transcript page.

    Args:
        page: The page HTML.
        url: Where it came from; the numeric id in the path becomes ``id``.

    Returns:
        The transcript. Paragraphs from the trailing copyright block onward are
        dropped, as is the leading "Guest:" line, which becomes ``guests``.
    """
    soup = BeautifulSoup(page, "html.parser")
    headline = soup.find("h1", class_="entry-title")
    title = normalize_space(headline.get_text()) if headline else None
    program = None
    aired: date | None = None
    if title and (match := LEGACY_TITLE.match(title)):
        program = match["program"].strip()
        aired = parse_legacy_date(match["date"])
    stamp = soup.find("abbr", class_="dtstamp")
    aired_time = None
    if isinstance(stamp, Tag) and stamp.get("title"):
        try:
            stamped = datetime.fromisoformat(str(stamp["title"]))
        except ValueError:
            stamped = None
        if stamped:
            aired_time = stamped.strftime("%H:%M")
            aired = aired or stamped.date()

    body = soup.find("div", id="intelliTXT")
    paragraphs = _paragraphs(body) if isinstance(body, Tag) else []
    guests = None
    if paragraphs and GUESTS_PREFIX.match(paragraphs[0]):
        guests = _guests(paragraphs.pop(0))
    for index, line in enumerate(paragraphs):
        if LEGACY_TAIL.match(line):
            paragraphs = paragraphs[:index]
            break
    text = "\n".join(paragraphs)
    ids = re.findall(r"/id/(\d+)/", url)
    return Transcript(
        id=ids[0] if ids else url.rstrip("/").rsplit("/", 1)[-1],
        url=url,
        title=title,
        program=program,
        aired_date=aired,
        aired_time=aired_time,
        guests=guests,
        summary=None,
        text=text,
        wordcount=len(text.split()),
        show_ids=[],
        source="legacy",
    )
