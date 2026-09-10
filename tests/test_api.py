import gzip
import json
from pathlib import Path

from msnbc_transcripts import api

FIXTURE = Path(__file__).parent / "fixtures" / "api_post_564760.json"


class FakeResponse:
    def __init__(self, payload, total_pages=1):
        self._payload = payload
        self.headers = {"X-WP-TotalPages": str(total_pages)}

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeSession:
    """Two pages: the fixture post, then a second post with an attached show."""

    request_timeout = 5.0

    def __init__(self):
        self.calls = []
        post = json.loads(FIXTURE.read_text())
        second = dict(
            post, id=1, link="https://www.ms.now/transcript/second", show=[132]
        )
        self.pages = {1: [post], 2: [second]}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        if url.endswith("/show"):
            return FakeResponse([{"id": 132, "name": "11th Hour with Stephanie Ruhle"}])
        return FakeResponse(self.pages[params["page"]], total_pages=2)


def test_scrape_writes_jsonl_and_html_and_resumes(tmp_path):
    out = tmp_path / "msnbc.jsonl"
    html_dir = tmp_path / "html"
    first = api.scrape(
        out, html_dir, requests_per_minute=100_000, session=FakeSession()
    )
    assert (first.pages, first.written, first.skipped, first.failed) == (2, 2, 0, [])
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert [r["id"] for r in rows] == ["564760", "1"]
    assert rows[0]["aired_date"] == "2022-10-04"
    assert rows[0]["shows"] is None
    assert rows[1]["shows"] == ["11th Hour with Stephanie Ruhle"]
    with gzip.open(html_dir / "564760.html.gz", "rt") as handle:
        assert "Summary" in handle.read()

    again = FakeSession()
    second = api.scrape(out, html_dir, requests_per_minute=100_000, session=again)
    assert (second.written, second.skipped) == (0, 2)
    assert all(not url.endswith("/show") for url, _ in again.calls)
    assert len(out.read_text().splitlines()) == 2


def test_since_and_limit(tmp_path):
    from datetime import datetime

    session = FakeSession()
    summary = api.scrape(
        tmp_path / "o.jsonl",
        tmp_path / "h",
        since=datetime(2025, 6, 1),  # noqa: DTZ001
        limit=1,
        requests_per_minute=100_000,
        session=session,
    )
    assert summary.written == 1
    assert session.calls[0][1]["after"] == "2025-06-01T00:00:00"
    assert len(session.calls) == 1
