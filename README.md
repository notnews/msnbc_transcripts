# MSNBC Transcripts 2008–2022

[![CI](https://github.com/notnews/msnbc_transcripts/actions/workflows/ci.yml/badge.svg)](https://github.com/notnews/msnbc_transcripts/actions/workflows/ci.yml)
[![Data](https://img.shields.io/badge/data-Dataverse-blue)](https://doi.org/10.7910/DVN/UPJDE1)
[![Code license](https://img.shields.io/badge/code-MIT-green)](LICENSE)

Tools and provenance for MSNBC transcript collections from NBC-hosted legacy pages, MSNBC listing pages, and the ms.now WordPress API. These sources overlap and have different coverage.

## Data

| Release | Files | Coverage | Rows | DOI |
|---|---|---|---:|---|
| API collection | `msnbc_transcripts_api_2010-2022_metadata.csv`, `msnbc_transcripts_api_2010-2022.tar.gz`, `msnbc_shows_api.csv` | 2010-05-27–2022-10-04 | 10,739, verified locally | [UPJDE1](https://doi.org/10.7910/DVN/UPJDE1) |
| Legacy NBC-hosted corpus | Raw HTML and parsed CSV | 2008–2014 | 5,369, historical release count | [ND1TCV](https://doi.org/10.7910/DVN/ND1TCV) |
| 2025 listing-page collection | `msnbc_transcripts_2022.csv.gz` | 2017-04-30–2025-03-15 | 3,451, historically reported; not reverified | [UPJDE1](https://doi.org/10.7910/DVN/UPJDE1) |

Counts describe the releases or local files identified above. Dataverse metadata requests returned HTTP 403 on 2026-09-10, so historical release counts could not all be reverified.

## Column dictionary

| Columns | Type | Description |
|---|---|---|
| `id`, `url` | string | Source identifier and original URL; deduplication uses exact URL, first input wins |
| `title`, `program` | string | Headline and program label parsed from title or legacy column |
| `aired_date`, `aired_time` | date, string | API publication date/time or historical airing fields; these are not guaranteed equivalent |
| `guests`, `summary` | string | Supplied guest list and summary, when available |
| `text`, `wordcount` | string, int32 | Transcript and whitespace word count; null when a required HTML file is missing |
| `source` | string | Input filename |

API JSONL also retains `show_ids`, `shows`, and source metadata. Empty taxonomy arrays produce `shows: null`. Saved API HTML files are `{id}.html.gz`.

## Coverage and known gaps

The original API result of 10,744 posts was trimmed to 10,739 through 2022-10-04. The release has a September 2010–June 2011 gap. All 10,739 local metadata rows have empty `show_ids`; this reflects missing post-to-taxonomy assignments in the response, not proof that the programs are unknown. The 216-entry shows CSV contains taxonomy counts, not verified transcript counts per show. New scraping resolves `/show?post=<id>` only for posts carrying show IDs.

Legacy dates contain typos such as “Thusday” and “Februrary”. The NBC repository documents the same ND1TCV corpus; do not add its count as a separate collection. The unsupported “16k transcripts from 2003–2014” claim has been removed. Exact-URL deduplication does not resolve aliases across msnbc.com and ms.now.

## Collection methods

| Era | Method |
|---|---|
| 2014 legacy | Parse `div#intelliTXT` from NBC pages; original scripts were Python 2 |
| 2025 | Discover listing pages and parse MSNBC HTML |
| 2026 onward | Page through `/wp-json/wp/v2/transcript`, following `X-WP-TotalPages`; resume by post ID |

The pre-cleanup implementation is preserved at [285ec65](https://github.com/notnews/msnbc_transcripts/tree/285ec65). New fetches write checkpoints under `data/`; reruns skip successful records and retry failures. Pure parsers read saved responses without accessing the network. Fixture provenance is in [tests/fixtures/SOURCES.md](tests/fixtures/SOURCES.md).

An interrupted, unterminated final JSONL record is removed before resuming; complete records are preserved. A valid final record missing only its newline is retained. Malformed complete lines remain errors.

## Usage

Python 3.12 or later and [uv](https://docs.astral.sh/uv/) are required. Run these commands from the repository root. Keep downloaded inputs and generated files under ignored `data/`.

### Install

```sh
uv sync --frozen --group dev
```

### Collect

```sh
uv run msnbc-transcripts scrape --since 2025-06-01 --limit 5
```

### Convert

```sh
uv run msnbc-transcripts to-parquet data/transcripts.jsonl --out data/transcripts.parquet
uv run msnbc-transcripts to-parquet data/msnbc_transcripts_api_2010-2022_metadata.csv --html-dir data/transcripts_html --out data/api.parquet
```

### Upload

The `upload` command reads `DATAVERSE_API_TOKEN` from the environment and adds the specified file to Dataverse. It does not publish a dataset version.

```sh
uv run msnbc-transcripts upload data/transcripts.parquet
```

## Development

Run the local checks:

```sh
make check
```

This runs Ruff, formatting, pytest, and pre-commit. Run `make ci-docker` to check lint and tests in standard Python 3.12 and 3.14 Docker images. CI uses the same lockfile and checks. Install the Git hooks with `uv run pre-commit install`.

## Citation

Use [CITATION.cff](CITATION.cff) and cite the relevant [Dataverse release](https://doi.org/10.7910/DVN/UPJDE1), including its version and DOI.

## License

Code is [MIT licensed](LICENSE). News text, abstracts, and archived pages retain their owners' rights; a code license does not grant rights to those materials. Consult the terms of the linked data release.
