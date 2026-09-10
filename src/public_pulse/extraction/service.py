"""Extraction service orchestrator and CLI entrypoint for Public Pulse (Phase 6).

Coordinates YouTube channel, program, video, and comment extraction, persisting
raw text into PostgreSQL via the Phase 5B repository layer. Tracks progress
and stats in PipelineRun records.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from public_pulse.database.models import PipelineRun, PipelineRunStatusEnum
from public_pulse.database.repository import (
    upsert_channel,
    upsert_comment,
    upsert_program,
    upsert_video,
)
from public_pulse.database.session import SessionLocal
from public_pulse.extraction.comment_fetcher import CommentFetcher
from public_pulse.extraction.config import ExtractionConfig, ProgramConfig
from public_pulse.extraction.exceptions import ExtractionError
from public_pulse.extraction.parsers import parse_channel_item
from public_pulse.extraction.video_discovery import VideoDiscovery
from public_pulse.extraction.youtube_client import YouTubeClient

log = logging.getLogger(__name__)


class ExtractionService:
    """Orchestrates YouTube Data API extraction for Public Pulse."""

    def __init__(self, config: ExtractionConfig, client: Optional[YouTubeClient] = None):
        self.config = config
        self.client = client or YouTubeClient(api_key=config.api_key)
        self.video_discovery = VideoDiscovery(self.client)
        self.comment_fetcher = CommentFetcher(self.client)

    def run_extraction(
        self,
        program_name_filter: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Run the extraction pipeline across target programs."""
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True

        pipeline_run = PipelineRun(
            run_type="youtube_extraction",
            started_at=datetime.now(timezone.utc),
            status=PipelineRunStatusEnum.running,
            triggered_by="extraction_service",
            comments_processed=0,
            comments_scored=0,
            comments_noise=0,
        )
        if not self.config.dry_run:
            db.add(pipeline_run)
            db.flush()

        stats = {
            "run_id": str(pipeline_run.id) if pipeline_run.id else "dry_run",
            "programs_processed": 0,
            "videos_discovered": 0,
            "videos_inserted": 0,
            "comments_discovered": 0,
            "comments_inserted": 0,
            "comments_updated": 0,
            "errors": [],
            "status": "success",
        }

        # Filter target programs
        target_programs = self.config.programs
        if program_name_filter:
            target_programs = [
                p for p in target_programs if p.program_name.lower() == program_name_filter.lower()
            ]
            if not target_programs:
                err_msg = f"Program {program_name_filter!r} not found in configuration."
                log.error(err_msg)
                stats["status"] = "error"
                stats["errors"].append(err_msg)
                if own_db:
                    db.close()
                return stats

        log.info("Starting YouTube extraction for %d programs (dry_run=%s)", len(target_programs), self.config.dry_run)

        try:
            for program_cfg in target_programs:
                log.info("Processing program: %r (Channel: %s)", program_cfg.program_name, program_cfg.channel_id)
                self._extract_program(program_cfg, db, stats)
                stats["programs_processed"] += 1

            if not self.config.dry_run:
                pipeline_run.status = PipelineRunStatusEnum.success
                pipeline_run.finished_at = datetime.now(timezone.utc)
                pipeline_run.comments_processed = stats["comments_discovered"]
                db.commit()

        except Exception as exc:
            log.exception("Extraction failed with error: %s", exc)
            stats["status"] = "error"
            stats["errors"].append(str(exc))
            if not self.config.dry_run:
                pipeline_run.status = PipelineRunStatusEnum.error
                pipeline_run.finished_at = datetime.now(timezone.utc)
                pipeline_run.error_message = str(exc)
                db.commit()

        finally:
            if own_db:
                db.close()

        log.info(
            "Extraction completed. Programs: %d, Videos: %d, Comments: %d (Inserted: %d, Updated: %d)",
            stats["programs_processed"],
            stats["videos_discovered"],
            stats["comments_discovered"],
            stats["comments_inserted"],
            stats["comments_updated"],
        )

        return stats

    def _extract_program(
        self,
        program_cfg: ProgramConfig,
        db: Session,
        stats: Dict[str, Any],
    ) -> None:
        """Extract channel, program, videos, and comments for a single program configuration."""
        # 1. Fetch channel metadata and upsert Channel record (guarantees 1 row per youtube_channel_id)
        try:
            ch_resp = self.client.get_channel_metadata(program_cfg.channel_id)
            items = ch_resp.get("items", [])
            if items:
                ch_meta = parse_channel_item(items[0])
            else:
                ch_meta = {
                    "youtube_channel_id": program_cfg.channel_id,
                    "name": f"Channel_{program_cfg.channel_id}",
                }
        except Exception as exc:
            log.warning("Could not fetch channel metadata for %s: %s", program_cfg.channel_id, exc)
            ch_meta = {
                "youtube_channel_id": program_cfg.channel_id,
                "name": f"Channel_{program_cfg.channel_id}",
            }

        channel_row = upsert_channel(
            db,
            youtube_channel_id=ch_meta["youtube_channel_id"],
            name=ch_meta["name"],
            channel_url=ch_meta.get("channel_url"),
            description=ch_meta.get("description"),
            subscriber_count=ch_meta.get("subscriber_count"),
        )

        # 2. Upsert Program record linked to Channel
        program_row = upsert_program(
            db,
            channel_id=channel_row.id,
            name=program_cfg.program_name,
            platform="youtube",
            program_type=program_cfg.program_type,  # remains None
        )

        # 3. Discover videos
        discovered_videos = self.video_discovery.discover_for_program(
            program=program_cfg,
            limit_videos=self.config.limit_videos,
            since=self.config.since,
            until=self.config.until,
        )

        stats["videos_discovered"] += len(discovered_videos)

        # Map to resolve parent_comment_id during comment insertion
        comment_id_map: Dict[str, Any] = {}

        for d_video in discovered_videos:
            meta = d_video.metadata
            video_row = upsert_video(
                db,
                program_id=program_row.id,
                youtube_video_id=meta["youtube_video_id"],
                title=meta.get("title"),
                description=meta.get("description"),
                published_at=meta.get("published_at"),
                duration_seconds=meta.get("duration_seconds"),
                is_live=meta.get("is_live", False),
                comment_count=meta.get("comment_count"),
            )
            stats["videos_inserted"] += 1

            # 4. Fetch comments for this video
            raw_comments = self.comment_fetcher.fetch_comments_for_video(
                video_id=meta["youtube_video_id"],
                limit_comments=self.config.limit_comments,
            )

            stats["comments_discovered"] += len(raw_comments)

            # Insert top-level comments first, then replies
            top_level_comments = [c for c in raw_comments if not c.get("is_reply")]
            reply_comments = [c for c in raw_comments if c.get("is_reply")]

            for c_data in top_level_comments + reply_comments:
                parent_db_id = None
                if c_data.get("parent_comment_id"):
                    parent_db_id = comment_id_map.get(c_data["parent_comment_id"])

                # Check if exists to count inserted vs updated
                from sqlalchemy import select
                from public_pulse.database.models import Comment
                existing = db.execute(
                    select(Comment).where(Comment.youtube_comment_id == c_data["youtube_comment_id"])
                ).scalar_one_or_none()

                c_row = upsert_comment(
                    db,
                    video_id=video_row.id,
                    youtube_comment_id=c_data["youtube_comment_id"],
                    text_raw=c_data["text_raw"],
                    text_clean=c_data["text_clean"],
                    author_hash=c_data.get("author_hash"),
                    like_count=c_data.get("like_count", 0),
                    reply_count=c_data.get("reply_count", 0),
                    posted_at=c_data.get("posted_at"),
                    is_reply=c_data.get("is_reply", False),
                    parent_comment_id=parent_db_id,
                )

                comment_id_map[c_data["youtube_comment_id"]] = c_row.id

                if existing is None:
                    stats["comments_inserted"] += 1
                else:
                    stats["comments_updated"] += 1

        if not self.config.dry_run:
            db.flush()


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Public Pulse YouTube Data Extraction CLI (Phase 6)"
    )
    parser.add_argument("--program", type=str, help="Single program name to extract")
    parser.add_argument("--all", action="store_true", help="Extract all configured programs")
    parser.add_argument("--limit-videos", type=int, default=None, help="Max videos per program")
    parser.add_argument("--limit-comments", type=int, default=None, help="Max comments per video")
    parser.add_argument("--since", type=str, default=None, help="ISO start date filter")
    parser.add_argument("--until", type=str, default=None, help="ISO end date filter")
    parser.add_argument("--dry-run", action="store_true", help="Run without persisting to DB")
    return parser.parse_args(args)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_args()

    try:
        config = ExtractionConfig.load(
            require_api_key=not args.dry_run,
            limit_videos=args.limit_videos,
            limit_comments=args.limit_comments,
            since=args.since,
            until=args.until,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        log.error("Configuration error: %s", exc)
        sys.exit(1)

    service = ExtractionService(config)
    result = service.run_extraction(program_name_filter=args.program)

    if result["status"] == "error":
        log.error("Extraction finished with errors: %s", result["errors"])
        sys.exit(1)
    else:
        log.info("Extraction completed successfully.")


if __name__ == "__main__":
    main()
