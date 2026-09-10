#!/usr/bin/env python3
"""Data cleaning and maintenance script for Public Pulse.

Resets errored comments back to 'pending' for re-inference and cleans orphaned records.
Usage:
    python scripts/clean_data.py --reset-errors
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from public_pulse.database.session import SessionLocal
from public_pulse.database.models import Comment

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean database records and reset failed jobs.")
    parser.add_argument("--reset-errors", action="store_true", help="Reset 'error' status comments back to 'pending'.")
    args = parser.parse_args()

    print("=" * 72)
    print("Public Pulse — Data Cleaning Tool")
    print("=" * 72)

    db = SessionLocal()
    try:
        if args.reset_errors:
            rows = db.query(Comment).filter(Comment.processing_status == "error").all()
            for r in rows:
                r.processing_status = "pending"
            db.commit()
            print(f"[OK] Reset {len(rows)} errored comments to 'pending'.")
        else:
            print("No action specified. Use --reset-errors to convert error comments to pending.")

        print("=" * 72)
        return 0

    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Data cleaning failed: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
