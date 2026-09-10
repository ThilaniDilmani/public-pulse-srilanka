#!/usr/bin/env python3
"""Historical scraper script for Public Pulse (Phase 6).

Scrapes target YouTube channels and programs configured in configs/programs.yaml.
Deduplicates against existing videos/comments before persisting to PostgreSQL.
Usage:
    python scripts/scrape_historical.py --limit-videos 5
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from public_pulse.database.session import SessionLocal
from public_pulse.extraction.config import ExtractionConfig
from public_pulse.extraction.service import ExtractionService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("scrape_historical")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape historical YouTube videos and comments for Public Pulse.")
    parser.add_argument("--limit-videos", type=int, default=5, help="Max videos per program (default: 5).")
    parser.add_argument("--program", type=str, default=None, help="Filter by specific program name.")
    args = parser.parse_args()

    print("=" * 72)
    print("Public Pulse — Historical Scraper")
    print("=" * 72)

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[ERROR] YOUTUBE_API_KEY environment variable is not set.")
        return 1

    try:
        config = ExtractionConfig.load(
            require_api_key=True,
            limit_videos=args.limit_videos,
        )
        service = ExtractionService(config)

        db = SessionLocal()
        try:
            stats = service.run_extraction(program_name_filter=args.program, db=db)
            print("\nExtraction Summary:")
            print(f"  Status:              {stats.get('status')}")
            print(f"  Programs processed:  {stats.get('programs_processed')}")
            print(f"  Videos discovered:   {stats.get('videos_discovered')}")
            print(f"  Comments discovered: {stats.get('comments_discovered')}")
            print(f"  Comments inserted:   {stats.get('comments_inserted')}")
            print(f"  Comments updated:    {stats.get('comments_updated')}")
            if stats.get("errors"):
                print("  Errors:")
                for err in stats["errors"]:
                    print(f"    - {err}")
        finally:
            db.close()

        print("=" * 72)
        print("Scrape completed successfully.")
        return 0

    except Exception as exc:
        log.exception("Historical scrape failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
