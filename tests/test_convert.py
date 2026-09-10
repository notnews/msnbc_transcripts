import gzip
import json
from datetime import date

import pyarrow.parquet as pq

from msnbc_transcripts import convert

API_HEADER = "id,date,title,url,slug,guests,show_ids,modified\n"
LISTING_HEADER = (
    "air_date,show_name,headline,guests,url,channel.name,program.name,uid,duration,"
    "year,month,date,time,timezone,path,wordcount,subhead,summary,text\n"
)


def test_three_sources_merge_dedupe_and_type(tmp_path):
    html_dir = tmp_path / "transcripts_html"
    html_dir.mkdir()
    with gzip.open(html_dir / "10.html.gz", "wt") as h:
        h.write(
            "<h2>Summary</h2><p>Sum.</p><h2>Transcript</h2><p>A b c.</p><p>D e.</p>"
        )
    meta = tmp_path / "x_metadata.csv"
    meta.write_text(
        API_HEADER
        + '10,2022-10-04T23:00:00,"Transcript: The Beat with Ari Melber, 10/4/22",'
        'https://www.ms.now/transcript/beat,beat,"Guests: A, B",,2022-10-04T23:00:00\n'
        "11,2021-01-01T20:00:00,Transcript: Missing HTML,https://www.ms.now/transcript/m,"
        "m,,,2021-01-01T20:00:00\n"
    )
    listing = tmp_path / "msnbc_transcripts_2022.csv"
    listing.write_text(
        LISTING_HEADER + "2025-03-15,Deadline: White House,Headline,Guests: C,"
        "https://www.msnbc.com/transcripts/d,MSNBC,,d1,,2025,3,15,16:00,"
        "UTC,,2,,Short,one two\n"
    )
    jsonl = tmp_path / "smoke.jsonl"
    jsonl.write_text(
        json.dumps(
            {
                "id": "10",
                "url": "https://www.ms.now/transcript/beat",  # duplicate of the CSV row
                "title": "dup",
                "aired_date": "2022-10-04",
                "text": "dup",
                "wordcount": 1,
            }
        )
        + "\n"
    )

    records, dropped = convert.load_records([meta, listing, jsonl], html_dir)
    assert dropped == 1
    table = convert.write_parquet(records, tmp_path / "out.parquet")
    back = pq.read_table(tmp_path / "out.parquet")
    assert back.schema.equals(convert.SCHEMA)
    rows = back.to_pylist()
    assert [r["id"] for r in rows] == ["11", "10", "d1"]  # sorted by aired_date
    beat = rows[1]
    assert beat["program"] == "The Beat with Ari Melber"
    assert beat["aired_date"] == date(2022, 10, 4)
    assert beat["aired_time"] == "23:00"
    assert beat["guests"] == "A, B"
    assert beat["summary"] == "Sum."
    assert beat["text"] == "A b c.\nD e."
    assert beat["wordcount"] == 5
    assert rows[0]["text"] is None
    assert rows[0]["wordcount"] is None
    assert rows[2]["program"] == "Deadline: White House"
    assert rows[2]["guests"] == "C"

    summary = convert.describe(table, dropped)
    assert "rows: 3" in summary
    assert "2022: 1" in summary
    assert "empty transcripts: 1" in summary
