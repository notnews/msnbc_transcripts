"""Scraper and provenance record for the MSNBC Transcripts 2008--2022 corpus."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("msnbc-transcripts")
except PackageNotFoundError:  # pragma: no cover - not installed
    __version__ = "0.0.0"
