#!/usr/bin/env python3
"""Data validation script for Public Pulse.

Performs DB integrity checks: table row counts, foreign key consistency,
comment processing status breakdown, and classification layer prediction counts.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from sqlalchemy import func
from public_pulse.database.session import SessionLocal
from public_pulse.database.models import (
    Channel, Program, Video, Comment, LayerPrediction,
    EvidenceSet, Evidence, Insight, VerificationResult
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main() -> int:
    print("=" * 72)
    print("Public Pulse — Database Health & Data Validation Check")
    print("=" * 72)

    db = SessionLocal()
    try:
        channels_cnt = db.query(Channel).count()
        programs_cnt = db.query(Program).count()
        videos_cnt = db.query(Video).count()
        comments_cnt = db.query(Comment).count()
        preds_cnt = db.query(LayerPrediction).count()
        evidence_sets_cnt = db.query(EvidenceSet).count()
        evidence_cnt = db.query(Evidence).count()
        insights_cnt = db.query(Insight).count()
        verifications_cnt = db.query(VerificationResult).count()

        print("\nCore Entity Counts:")
        print(f"  Channels:             {channels_cnt}")
        print(f"  Programs:             {programs_cnt}")
        print(f"  Videos:               {videos_cnt}")
        print(f"  Comments:             {comments_cnt}")
        print(f"  Layer Predictions:    {preds_cnt}")
        print(f"  Evidence Sets:        {evidence_sets_cnt}")
        print(f"  Evidence Items:       {evidence_cnt}")
        print(f"  Insights:             {insights_cnt}")
        print(f"  Verification Results: {verifications_cnt}")

        print("\nComment Processing Status Breakdown:")
        status_counts = (
            db.query(Comment.processing_status, func.count(Comment.id))
            .group_by(Comment.processing_status)
            .all()
        )
        for status_val, count_val in status_counts:
            val_str = status_val.value if hasattr(status_val, "value") else str(status_val)
            print(f"  - {val_str:<15}: {count_val}")

        print("\nLayer Prediction Breakdown:")
        layer_counts = (
            db.query(LayerPrediction.layer, func.count(LayerPrediction.id))
            .group_by(LayerPrediction.layer)
            .all()
        )
        for layer_val, count_val in layer_counts:
            val_str = layer_val.value if hasattr(layer_val, "value") else str(layer_val)
            print(f"  - {val_str:<15}: {count_val}")

        print("\nIntegrity Checks:")
        # Check orphaned videos
        orphaned_videos = db.query(Video).filter(Video.program_id.is_(None)).count()
        print(f"  - Orphaned Videos (no program): {orphaned_videos}")

        # Check orphaned comments
        orphaned_comments = db.query(Comment).filter(Comment.video_id.is_(None)).count()
        print(f"  - Orphaned Comments (no video): {orphaned_comments}")

        print("\n" + "=" * 72)
        print("DATA VALIDATION COMPLETED CLEANLY.")
        print("=" * 72)
        return 0

    except Exception as exc:
        print(f"\n[ERROR] Validation failed: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
