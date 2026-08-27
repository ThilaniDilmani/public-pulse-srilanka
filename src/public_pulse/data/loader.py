"""Load raw/interim/processed comment data and write validated dataframes."""


def load_raw(source_path: str):
    """Load a raw scraped export (CSV/XLSX) without modifying it."""
    raise NotImplementedError


def dedup(df):
    """Drop duplicate comments (same video_id + author_hash + text)."""
    raise NotImplementedError


def validate_schema(df):
    """Check required columns exist and types are correct."""
    raise NotImplementedError
