# MSNBC Transcripts

Collection of MSNBC show transcripts from 2010–2022.

## Download

All data are available on Harvard Dataverse:
https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/UPJDE1

## Available Data

### API Scrape (May 2026) — Recommended

10,739 transcripts across 216 shows, May 2010 – October 2022.

| Year | Transcripts |
|------|-------------|
| 2010 | 43 |
| 2011 | 115 |
| 2012 | 233 |
| 2013 | 237 |
| 2014 | 217 |
| 2015 | 994 |
| 2016 | 906 |
| 2017 | 1,185 |
| 2018 | 1,467 |
| 2019 | 1,475 |
| 2020 | 1,288 |
| 2021 | 1,471 |
| 2022 | 1,108 |

**Files:**
- `msnbc_transcripts_api_2010-2022.tar.gz` — HTML transcript files (186MB)
- `msnbc_transcripts_api_2010-2022_metadata.csv` — metadata for all transcripts
- `msnbc_shows_api.csv` — show list with transcript counts

### Earlier Scrapes

- **2003–2014 scrape**: 16k transcripts from an earlier collection
- **2025 HTML scrape**: `msnbc_transcripts_2022.csv.gz` — transcripts from 2020–2025 scraped from listing pages

## Data Format

### Metadata CSV (`msnbc_transcripts_api_2010-2022_metadata.csv`)

| Column | Description |
|--------|-------------|
| `id` | Unique transcript ID |
| `date` | Publication date (ISO 8601) |
| `title` | Transcript title |
| `url` | Original URL |
| `slug` | URL slug |
| `guests` | Guest names |
| `show_ids` | Associated show IDs |
| `modified` | Last modified date |

### Shows CSV (`msnbc_shows_api.csv`)

| Column | Description |
|--------|-------------|
| `id` | Show ID |
| `name` | Show name |
| `slug` | URL slug |
| `count` | Number of transcripts |

### HTML Files

Each transcript is saved as an HTML file named `{id}.html` containing the full transcript text.

## Scripts

For reproducibility or extending the dataset:

- [WordPress API Scraper](scripts/msnbc_api.py) — REST API scraper (recommended)
- [HTML Scraper](scripts/msnbc.py) — scrapes transcript listing pages
- [Quick Peek](scripts/peek_file.ipynb) — preview data
- [Upload to Dataverse](scripts/upload_to_dataverse.ipynb)
