### MSNBC Transcripts: 2010--2022

We scraped https://www.msnbc.com/transcripts to get all the transcripts from 2010--2021.

```
year	 n_transcripts
2010      43
2011     115
2012     205
2013     175
2014     217
2015     986
2016     907
2017    1185
2018    1468
2019    1475
2020    1286
2021    1476
2022     131
```

When I scraped in 03/2025, I got the following (so essentially 2022)

```
year
2017       2
2020     703
2021    1479
2022    1156
2023      52
2024      48
2025      11
```

### WordPress API Scrape (05/2026)

A more comprehensive scrape using the WordPress REST API (`scripts/msnbc_api.py`) retrieved **10,739 transcripts** across **216 shows** from May 2010 through October 2022.

```
year   n_transcripts
2010       43
2011      115
2012      233
2013      237
2014      217
2015      994
2016      906
2017     1185
2018     1467
2019     1475
2020     1288
2021     1471
2022     1108
```

### Scripts

1. [HTML Scraper](scripts/msnbc.py) - scrapes transcript listing pages
2. [WordPress API Scraper](scripts/msnbc_api.py) - uses REST API to fetch transcripts
3. [Quick Peek](scripts/peek_file.ipynb)
4. [Upload to Dataverse](scripts/upload_to_dataverse.ipynb)

### Data

**May 2026 API scrape:**
- `data/msnbc_transcripts_api_2010-2022.tar.gz` (186MB) - 10,739 HTML transcript files
- `data/msnbc_transcripts_api_2010-2022_metadata.csv` - metadata for all transcripts
- `data/msnbc_shows_api.csv` - 216 shows with transcript counts

**Previous scrapes:**
- The final data posted on the Harvard Dataverse includes 16k scripts spanning 2003--2014 that were scraped earlier
- The data scraped in 2025 is stored under `msnbc_transcripts_2022.csv.gz`

The data are posted at:
https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi%3A10.7910%2FDVN%2FUPJDE1
