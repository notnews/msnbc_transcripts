"""Command-line entry point: ``msnbc-transcripts scrape | to-parquet | upload``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from msnbc_transcripts import api, convert, upload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msnbc-transcripts")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scrape", help="append new transcripts from the ms.now API")
    s.add_argument("--since", type=datetime.fromisoformat, help="ISO timestamp")
    s.add_argument("--limit", type=int, help="stop after this many new transcripts")
    s.add_argument("--out", type=Path, default=Path("data/transcripts.jsonl"))
    s.add_argument("--html-dir", type=Path, default=Path("data/transcripts_html"))
    s.add_argument("--log", type=Path, default=Path("data/scrape.log"))
    s.add_argument("--rpm", type=int, default=60, help="requests per minute")
    s.add_argument("--timeout", type=float, default=30.0, help="seconds per request")

    p = sub.add_parser("to-parquet", help="combine JSONL/CSV inputs into one Parquet")
    p.add_argument("inputs", type=Path, nargs="+")
    p.add_argument("--html-dir", type=Path, default=None)
    p.add_argument("--out", type=Path, required=True)

    u = sub.add_parser("upload", help="add a file to the Dataverse dataset")
    u.add_argument("file", type=Path)
    u.add_argument("--doi", default=upload.DATASET_DOI)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return an exit status."""
    args = _build_parser().parse_args(argv)
    if args.command == "scrape":
        args.log.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[logging.StreamHandler(), logging.FileHandler(args.log)],
        )
        summary = api.scrape(
            args.out,
            args.html_dir,
            since=args.since,
            limit=args.limit,
            requests_per_minute=args.rpm,
            session=api.make_session(timeout=args.timeout),
        )
        return 1 if summary.failed else 0
    if args.command == "to-parquet":
        records, dropped = convert.load_records(args.inputs, args.html_dir)
        table = convert.write_parquet(records, args.out)
        sys.stdout.write(convert.describe(table, dropped) + "\n")
        return 0
    if args.command == "upload":
        sys.stdout.write(upload.upload(args.file, args.doi) + "\n")
        return 0
    return 2  # pragma: no cover - argparse enforces the choices


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
