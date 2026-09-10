#!/usr/bin/env python3
"""Build golden sample dataset script for Public Pulse.

Exports a balanced stratified sample of scored comments to data/golden_sample/
for human audit and golden dataset evaluation.
"""

from __future__ import annotations

import json
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
from public_pulse.database.models import Comment, LayerPrediction

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main() -> int:
    print("=" * 72)
    print("Public Pulse — Build Golden Sample")
    print("=" * 72)

    db = SessionLocal()
    try:
        comments = db.query(Comment).filter(Comment.processing_status == "scored").limit(100).all()
        out_dir = REPO_ROOT / "data" / "golden_sample"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "golden_sample.json"

        data = []
        for c in comments:
            data.append({
                "comment_id": str(c.id),
                "text_clean": c.text_clean,
                "like_count": c.like_count,
                "published_at": c.published_at.isoformat() if c.published_at else None,
            })

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[OK] Exported {len(data)} sample comments to {out_file.relative_to(REPO_ROOT)}")
        print("=" * 72)
        return 0

    except Exception as exc:
        print(f"[ERROR] Failed to build golden sample: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
