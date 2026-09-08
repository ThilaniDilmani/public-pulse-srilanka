"""Catalog service encapsulating repository calls for channels, programs, and videos (Phase 11)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from public_pulse.database import repository
from api.schemas.catalog import ChannelOut, ProgramOut, VideoOut


class CatalogService:

    @staticmethod
    def get_channels(db: Session) -> List[ChannelOut]:
        channels = repository.list_channels(db)
        return [
            ChannelOut(
                id=str(c.id),
                name=c.name,
                channel_url=c.channel_url,
                description=c.description,
                subscriber_count=c.subscriber_count,
                created_at=c.created_at,
            )
            for c in channels
        ]

    @staticmethod
    def get_channel(db: Session, channel_id: str) -> Optional[ChannelOut]:
        c = repository.get_channel(db, channel_id)
        if not c:
            return None
        return ChannelOut(
            id=str(c.id),
            name=c.name,
            channel_url=c.channel_url,
            description=c.description,
            subscriber_count=c.subscriber_count,
            created_at=c.created_at,
        )

    @staticmethod
    def get_programs(
        db: Session, channel_id: Optional[str] = None, is_active: Optional[bool] = None
    ) -> List[ProgramOut]:
        programs = repository.list_programs(db, channel_id=channel_id, is_active=is_active)
        return [
            ProgramOut(
                id=str(p.id),
                channel_id=str(p.channel_id),
                channel_name=p.channel.name if p.channel else "",
                name=p.name,
                platform=p.platform,
                is_active=p.is_active,
                created_at=p.created_at,
            )
            for p in programs
        ]

    @staticmethod
    def get_program(db: Session, program_id: str) -> Optional[ProgramOut]:
        p = repository.get_program(db, program_id)
        if not p:
            return None
        return ProgramOut(
            id=str(p.id),
            channel_id=str(p.channel_id),
            channel_name=p.channel.name if p.channel else "",
            name=p.name,
            platform=p.platform,
            is_active=p.is_active,
            created_at=p.created_at,
        )

    @staticmethod
    def get_videos_for_program(
        db: Session,
        program_id: str,
        limit: int = 50,
        offset: int = 0,
        start_date=None,
        end_date=None,
    ) -> List[VideoOut]:
        videos = repository.list_videos_for_program(
            db, program_id, limit=limit, offset=offset, start_date=start_date, end_date=end_date
        )
        return [
            VideoOut(
                id=str(v.id),
                program_id=str(v.program_id),
                title=v.title,
                published_at=v.published_at,
                duration_seconds=v.duration_seconds,
                is_live=v.is_live,
                comment_count=v.comment_count,
                scraped_at=v.scraped_at,
            )
            for v in videos
        ]
