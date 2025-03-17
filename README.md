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

### Scripts

1. [Scrape](scripts/msnbc.py)
2. [Quick Peek](scripts/peek_file.ipynb)
3. [Upload to Dataverse][scripts/upload_to_dataverse.ipynb]

### Data

The final data posted on the Harvard Dataverse includes 16k scripts spanning 2003--2014 that were scraped earlier. The data scraped in 2025 is stored under `msnbc_transcripts_2022.csv.gz` 

The data are posted at:
https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi%3A10.7910%2FDVN%2FUPJDE1
