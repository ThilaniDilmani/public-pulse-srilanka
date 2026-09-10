#!/usr/bin/env python3
"""Live continuous YouTube scraper daemon for Public Pulse.

Polls target YouTube channels periodically to discover newly posted episodes
and extract new comments.
Usage:
    python scripts/scrape_live.py --interval-minutes 15
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
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
log = logging.getLogger("scrape_live")


def main() -> int:
    parser = argparse.ArgumentParser(description="Live polling scraper for Public Pulse.")
    parser.add_argument("--interval-minutes", type=int, default=30, help="Polling interval in minutes (default: 30).")
    parser.add_argument("--limit-videos", type=int, default=2, help="Max videos per program per run (default: 2).")
    parser.add_argument("--once", action="store_true", help="Run once and exit instead of continuous loop.")
    args = parser.parse_args()

    print("=" * 72)
    print("Public Pulse — Live Polling Scraper Daemon")
    print(f"Interval: {args.interval-minutes} min | Videos per program: {args.limit_videos}")
    print("=" * 72)

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[ERROR] YOUTUBE_API_KEY environment variable is missing.")
        return 1

    config = ExtractionConfig.load(
        require_api_key=True,
        limit_videos=args.limit_videos,
    )
    service = ExtractionService(config)

    while True:
        try:
            log.info("Starting live extraction cycle...")
            db = SessionLocal()
            try:
                stats = service.run_extraction(db=db)
                log.info(
                    "Cycle complete. Videos: %d, Comments inserted: %d",
                    stats.get("videos_discovered", 0),
                    stats.get("comments_inserted", 0),
                )
            finally:
                db.close()
        except Exception as exc:
            log.exception("Error during live extraction cycle: %s", exc)

        if args.once:
            break

        log.info("Sleeping for %d minutes...", args.interval_minutes)
        time.sleep(args.interval_minutes * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
