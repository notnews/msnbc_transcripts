import json
from datetime import date

from msnbc_transcripts.parsers import (
    parse_api_post,
    parse_legacy_date,
    parse_legacy_page,
    parse_rendered_html,
)

LEGACY_URL = "http://www.nbcnews.com/id/38935621/ns/msnbc-rachel_maddow_show/"


def test_parse_api_post(fixture_text):
    t = parse_api_post(json.loads(fixture_text("api_post_564760.json")))
    assert t.id == "564760"
    assert t.url.endswith("/transcript-11th-hour-stephanie-ruhle-10-4-22-n1299636")
    assert t.title == "Transcript: The 11th Hour with Stephanie Ruhle, 10/4/22"
    assert t.program == "The 11th Hour with Stephanie Ruhle"
    assert (t.aired_date, t.aired_time) == (date(2022, 10, 4), "23:00")
    assert t.guests.startswith("Melissa Murray, Zoe Tillman")
    assert t.summary.startswith("Trump`s team asked the high court")
    assert t.text.startswith("LAWRENCE O`DONNELL, MSNBC ANCHOR:")
    assert "[23:00:15]" in t.text
    assert "Summary" not in t.text
    assert t.wordcount == len(t.text.split()) > 30
    assert t.show_ids == []
    assert t.source == "api"


def test_rendered_html_without_headings_is_all_transcript():
    summary, text = parse_rendered_html("<p>HOST: hello.</p><p>GUEST: hi.</p>")
    assert summary is None
    assert text == "HOST: hello.\nGUEST: hi."


def test_degenerate_post_yields_empty_text():
    rendered = (
        '\n<h3 class="wp-block-heading">Summary</h3>\n\n\n'
        '<h3 class="wp-block-heading">Transcript</h3>'
    )
    summary, text = parse_rendered_html(rendered)
    assert (summary, text) == (None, "")
    post = {
        "id": 564304,
        "link": "https://www.ms.now/transcript/x",
        "date": "2022-01-01T10:00:00",
        "title": {"rendered": "Transcript: Deadline: White House, 1/1/22"},
        "content": {"rendered": rendered},
        "yoast_head_json": {"description": "Not a guest list"},
    }
    t = parse_api_post(post)
    assert (t.text, t.wordcount, t.guests) == ("", 0, None)
    assert t.program == "Deadline: White House"


def test_parse_legacy_page(fixture_text):
    t = parse_legacy_page(fixture_text("legacy_38935621.html"), LEGACY_URL)
    assert t.id == "38935621"
    assert t.title == "'The Rachel Maddow Show' for Monday, August 30th, 2010"
    assert t.program == "The Rachel Maddow Show"
    assert t.aired_date == date(2010, 8, 30)
    assert t.aired_time == "16:09"  # abbr.dtstamp title, the page's publish time
    assert t.guests == "Charles Stile, E.J. Dionne, Steve Kornacki"
    assert not t.text.startswith("Guest")
    assert "copyright" not in t.text.lower()
    assert t.wordcount == len(t.text.split()) > 20
    assert t.source == "legacy"


def test_legacy_date_tolerates_weekday_typos():
    assert parse_legacy_date("Thusday, February 17th, 2011") == date(2011, 2, 17)
    assert parse_legacy_date("Monday, August 30th, 2010") == date(2010, 8, 30)
    assert parse_legacy_date("Wednesday, October 01, 2013") == date(2013, 10, 1)
    assert parse_legacy_date("no date here") is None
