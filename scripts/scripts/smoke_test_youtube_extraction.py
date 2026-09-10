"""Controlled real YouTube API smoke test (Phase 6).

Requires YOUTUBE_API_KEY in environment or .env file.
Performs a small extraction: 1 program, 1 video, max 20 comments.
Verifies Channel -> Program -> Video -> Comments DB insertion, raw text preservation,
and idempotency across two sequential runs.
"""

import os
import sys
from pathlib import Path

# Add src/ to path
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv

load_dotenv()

from public_pulse.database.models import Channel, Comment, PipelineRun, Program, Video
from public_pulse.database.session import SessionLocal
from public_pulse.extraction.config import ExtractionConfig
from public_pulse.extraction.service import ExtractionService


def run_smoke_test():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("SKIP: YOUTUBE_API_KEY environment variable is not set. Skipping live API smoke test.")
        return True

    print("Running controlled live YouTube API smoke test...")

    # Load configuration
    config = ExtractionConfig.load(
        require_api_key=True,
        limit_videos=1,
        limit_comments=20,
    )

    service = ExtractionService(config)
    db = SessionLocal()

    try:
        # Run 1: Initial extraction for 1 program
        target_program = "Hiru Salakuna (Hiru)"
        print(f"Executing Run 1 for program: '{target_program}'...")
        stats1 = service.run_extraction(program_name_filter=target_program, db=db)

        if stats1["status"] != "success":
            print(f"FAIL: Run 1 failed with error: {stats1.get('errors')}")
            return False

        print(f"Run 1 completed: Discovered {stats1['videos_discovered']} video(s), "
              f"Inserted {stats1['comments_inserted']} comment(s).")

        # Verify DB records after Run 1
        channels_count = db.query(Channel).count()
        programs_count = db.query(Program).count()
        videos_count = db.query(Video).count()
        comments_count = db.query(Comment).count()

        print(f"DB State after Run 1 -> Channels: {channels_count}, Programs: {programs_count}, "
              f"Videos: {videos_count}, Comments: {comments_count}")

        if comments_count > 0:
            sample_comment = db.query(Comment).first()
            print(f"Sample Comment text_raw: {sample_comment.text_raw!r}")
            assert sample_comment.text_raw is not None, "text_raw must not be None"

        # Run 2: Re-run exact same extraction to verify Idempotency
        print("Executing Run 2 (Idempotency test)...")
        stats2 = service.run_extraction(program_name_filter=target_program, db=db)

        if stats2["status"] != "success":
            print(f"FAIL: Run 2 failed with error: {stats2.get('errors')}")
            return False

        print(f"Run 2 completed: Inserted {stats2['comments_inserted']} comment(s), "
              f"Updated {stats2['comments_updated']} comment(s).")

        assert stats2["comments_inserted"] == 0, "Idempotency failed: duplicate comments inserted on Run 2!"

        db_comments_after = db.query(Comment).count()
        assert db_comments_after == comments_count, "Comment count changed on second run!"

        print("SUCCESS: Live YouTube API smoke test and idempotency verification passed!")
        return True

    finally:
        db.close()


if __name__ == "__main__":
    success = run_smoke_test()
    if not success:
        sys.exit(1)
