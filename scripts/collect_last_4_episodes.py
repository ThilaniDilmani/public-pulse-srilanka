#!/usr/bin/env python3
"""
Public Pulse - collect the latest 4 episodes for selected programs.

This runner intentionally does NOT modify the shared database session/engine.
It creates a fresh SQLAlchemy SessionLocal() for every program and retries
recoverable database/network failures.

Selected programs:
    1. Hiru Salakuna (Hiru)
    2. Derana 360 (Derana)
    3. Hiru Balaya (Hiru)
    4. Sirasa Satana
    5. Wada pitiyaa (Ada derana)

Target:
    5 programs x 4 videos = up to 20 episodes/videos.

Requirements:
    - Run from the Public Pulse repository root.
    - YOUTUBE_API_KEY in .env/environment.
    - DATABASE_URL in .env/environment.
    - Existing Public Pulse extraction configuration/service.
    - Existing configs/programs.yaml containing the selected programs.

Usage:
    python scripts/collect_last_4_episodes.py

Optional environment variables:
    PP_COLLECTION_RETRIES=3
    PP_RETRY_DELAY_SECONDS=5
    PP_DB_VERIFY=true

Notes:
    - This script only collects YouTube data. It does not run preprocessing,
      model inference, evidence retrieval, Gemini, or faithfulness verification.
    - It relies on the existing ExtractionService for YouTube discovery and
      comment extraction.
    - Each program receives an independent DB session. A failed program does
      not poison the next program's SQLAlchemy session.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Repository / imports
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError, PendingRollbackError

from public_pulse.database.session import SessionLocal
from public_pulse.extraction.config import ExtractionConfig
from public_pulse.extraction.service import ExtractionService


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROGRAMS = [
    "Hiru Salakuna (Hiru)",
    "Derana 360 (Derana)",
    "Hiru Balaya (Hiru)",
    "Sirasa Satana",
    "Wada pitiyaa (Ada derana)",
]

EPISODES_PER_PROGRAM = 4

MAX_RETRIES = max(
    1,
    int(os.environ.get("PP_COLLECTION_RETRIES", "3")),
)

RETRY_DELAY_SECONDS = max(
    1,
    int(os.environ.get("PP_RETRY_DELAY_SECONDS", "5")),
)

VERIFY_DATABASE = (
    os.environ.get("PP_DB_VERIFY", "true").strip().lower()
    not in {"0", "false", "no", "off"}
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

log = logging.getLogger("public_pulse.collection_runner")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_header(title: str) -> None:
    print()
    print("=" * 76)
    print(title)
    print("=" * 76)


def require_environment() -> None:
    """Fail before contacting YouTube/DB when required configuration is absent."""
    missing = []

    if not os.environ.get("YOUTUBE_API_KEY", "").strip():
        missing.append("YOUTUBE_API_KEY")

    if not os.environ.get("DATABASE_URL", "").strip():
        missing.append("DATABASE_URL")

    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Set them in .env or the environment."
        )


def verify_database_connection() -> None:
    """Perform a small DB check before starting the real collection."""
    if not VERIFY_DATABASE:
        return

    db = SessionLocal()
    try:
        value = db.execute(text("SELECT 1")).scalar_one()
        if value != 1:
            raise RuntimeError(
                f"Database health check returned unexpected value: {value!r}"
            )
        print("Database connection: OK")
    finally:
        db.close()


def rollback_and_close(db: Any) -> None:
    """Best-effort cleanup of a failed SQLAlchemy session."""
    if db is None:
        return

    try:
        db.rollback()
    except Exception:
        pass

    try:
        db.close()
    except Exception:
        pass


def is_recoverable_database_error(exc: BaseException) -> bool:
    """
    Identify errors for which creating a fresh session and retrying is useful.

    We deliberately do not retry arbitrary exceptions indefinitely.
    """
    if isinstance(exc, PendingRollbackError):
        return True

    if isinstance(exc, OperationalError):
        return True

    if isinstance(exc, DBAPIError) and getattr(exc, "connection_invalidated", False):
        return True

    message = str(exc).lower()

    recoverable_fragments = (
        "server closed the connection unexpectedly",
        "connection unexpectedly closed",
        "connection is closed",
        "could not translate host name",
        "connection refused",
        "connection reset",
        "terminating connection",
        "connection timed out",
        "timeout expired",
        "ssl connection has been closed unexpectedly",
    )

    return any(fragment in message for fragment in recoverable_fragments)


def collect_one_program(
    service: ExtractionService,
    program_name: str,
) -> dict[str, Any]:
    """
    Collect one program using a completely fresh DB session.

    The ExtractionService remains responsible for the actual extraction.
    """
    db = None

    try:
        db = SessionLocal()

        print_header(
            f"PROGRAM: {program_name}\n"
            f"TARGET: latest {EPISODES_PER_PROGRAM} episodes"
        )

        print("Connecting to YouTube and discovering configured episodes...")
        log.info(
            "Starting program extraction: %s (limit_videos=%d)",
            program_name,
            EPISODES_PER_PROGRAM,
        )

        stats = service.run_extraction(
            program_name_filter=program_name,
            db=db,
        )

        # The current ExtractionService manages the transaction itself and
        # returns a structured status.
        if stats.get("status") != "success":
            raise RuntimeError(
                f"ExtractionService returned status={stats.get('status')!r}; "
                f"errors={stats.get('errors')!r}"
            )

        return stats

    finally:
        # Even after a successful service run, explicitly close the runner's
        # session so no connection remains checked out.
        if db is not None:
            try:
                db.close()
            except Exception:
                pass


def collect_with_retry(
    service: ExtractionService,
    program_name: str,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """
    Run one program with bounded retries.

    Every retry creates a new DB session. This is the central fix for the
    PendingRollbackError chain observed in the original runner.
    """
    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        db = None

        try:
            print(
                f"\nAttempt {attempt}/{MAX_RETRIES}: "
                f"{program_name}"
            )

            stats = collect_one_program(
                service=service,
                program_name=program_name,
            )

            return True, stats, None

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"

            # collect_one_program owns and closes its session. This variable
            # exists only for defensive cleanup if construction ever changes.
            rollback_and_close(db)

            print(f"Attempt {attempt} failed:")
            print(f"  {last_error}")

            if not is_recoverable_database_error(exc):
                print("  Error is not classified as recoverable; stopping retries.")
                break

            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY_SECONDS * attempt
                print(
                    f"  Recoverable connection/database error. "
                    f"Creating a fresh session and retrying in {wait}s..."
                )
                time.sleep(wait)

    return False, None, last_error


def print_program_result(
    program_name: str,
    stats: dict[str, Any],
) -> tuple[int, int, int]:
    """Print and return video/insert/update counts."""
    videos = int(stats.get("videos_discovered", 0) or 0)
    inserted = int(stats.get("comments_inserted", 0) or 0)
    updated = int(stats.get("comments_updated", 0) or 0)
    comments_discovered = int(stats.get("comments_discovered", 0) or 0)

    print()
    print(f"Completed: {program_name}")
    print(f"  Status:             {stats.get('status')}")
    print(f"  Videos discovered:  {videos}")
    print(f"  Comments discovered:{comments_discovered}")
    print(f"  Comments inserted:  {inserted}")
    print(f"  Comments updated:   {updated}")

    errors = stats.get("errors") or []
    if errors:
        print("  Reported errors:")
        for error in errors:
            print(f"    - {error}")

    return videos, inserted, updated


def verify_collected_programs() -> None:
    """
    Print a simple DB verification after collection.

    This does not require direct database credentials beyond DATABASE_URL and
    does not expose comment text or author information.
    """
    from public_pulse.database.models import Channel, Comment, Program, Video

    print_header("DATABASE VERIFICATION")

    db = SessionLocal()
    try:
        total_channels = db.query(Channel).count()
        total_programs = db.query(Program).count()
        total_videos = db.query(Video).count()
        total_comments = db.query(Comment).count()

        print(f"Total channels in DB:  {total_channels}")
        print(f"Total programs in DB:  {total_programs}")
        print(f"Total videos in DB:    {total_videos}")
        print(f"Total comments in DB:  {total_comments}")

        print()
        print("Selected-program counts:")

        for program_name in PROGRAMS:
            program = (
                db.query(Program)
                .filter(Program.name == program_name)
                .first()
            )

            if program is None:
                print(f"  {program_name}: NOT FOUND")
                continue

            video_count = (
                db.query(Video)
                .filter(Video.program_id == program.id)
                .count()
            )

            # Count comments through the selected program's videos without
            # loading comment bodies into Python.
            comment_count = (
                db.query(Comment)
                .join(Video, Comment.video_id == Video.id)
                .filter(Video.program_id == program.id)
                .count()
            )

            print(
                f"  {program_name}: "
                f"{video_count} videos, {comment_count} comments"
            )

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("Public Pulse - Last 4 Episode Comment Collector")
    print("=" * 76)
    print(f"Programs: {len(PROGRAMS)}")
    print(f"Episodes per program: {EPISODES_PER_PROGRAM}")
    print(f"Maximum target videos: {len(PROGRAMS) * EPISODES_PER_PROGRAM}")
    print(f"Retries per program: {MAX_RETRIES}")
    print()

    try:
        require_environment()
        verify_database_connection()

        # One ExtractionService can safely be reused because the DB Session is
        # deliberately supplied separately for every program.
        config = ExtractionConfig.load(
            require_api_key=True,
            limit_videos=EPISODES_PER_PROGRAM,
            # IMPORTANT: limit_comments remains None, meaning no artificial
            # per-video comment cap is imposed by this runner.
        )

        configured_names = {
            program.program_name.lower()
            for program in config.programs
        }

        missing_programs = [
            name
            for name in PROGRAMS
            if name.lower() not in configured_names
        ]

        if missing_programs:
            print()
            print("ERROR: The following selected programs are missing from")
            print("configs/programs.yaml:")
            for name in missing_programs:
                print(f"  - {name}")
            print()
            print("No collection was started.")
            return 1

        service = ExtractionService(config)

        total_videos = 0
        total_inserted = 0
        total_updated = 0
        failed_programs: list[tuple[str, str]] = []

        for index, program_name in enumerate(PROGRAMS, start=1):
            print()
            print(
                f"########## PROGRAM {index}/{len(PROGRAMS)} "
                f"##########"
            )

            success, stats, error = collect_with_retry(
                service=service,
                program_name=program_name,
            )

            if not success or stats is None:
                failed_programs.append(
                    (program_name, error or "Unknown extraction error")
                )
                continue

            videos, inserted, updated = print_program_result(
                program_name,
                stats,
            )

            total_videos += videos
            total_inserted += inserted
            total_updated += updated

        print_header("COLLECTION SUMMARY")

        print(f"Programs requested:       {len(PROGRAMS)}")
        print(f"Episodes requested:       {EPISODES_PER_PROGRAM} per program")
        print(
            f"Maximum episode target:   "
            f"{len(PROGRAMS) * EPISODES_PER_PROGRAM}"
        )
        print(f"Videos discovered:        {total_videos}")
        print(f"Comments inserted:        {total_inserted}")
        print(f"Comments updated:         {total_updated}")

        if failed_programs:
            print()
            print("FAILED PROGRAMS:")
            for name, error in failed_programs:
                print(f"  - {name}")
                print(f"      {error}")

            print()
            print(
                "The successful programs were kept in the database. "
                "You can rerun this script safely; existing records are "
                "handled by the existing extraction/upsert layer."
            )
        else:
            print()
            print("SUCCESS: all selected programs completed.")

        if VERIFY_DATABASE:
            verify_collected_programs()

        print()
        print("=" * 76)
        print("IMPORTANT")
        print("=" * 76)
        print(
            "This run only performs YouTube extraction and database storage."
        )
        print(
            "It does NOT automatically execute preprocessing, "
            "Layer 1/2/4 inference,"
        )
        print(
            "evidence retrieval, Gemini insight generation, or "
            "faithfulness verification."
        )

        return 1 if failed_programs else 0

    except KeyboardInterrupt:
        print()
        print("Collection interrupted by user.")
        return 130

    except Exception as exc:
        print()
        print("=" * 76)
        print("FATAL ERROR")
        print("=" * 76)
        print(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
