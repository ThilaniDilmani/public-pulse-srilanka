"""Catalog Pydantic response schemas (Phase 11).

Strictly preserves CHANNEL -> PROGRAM -> VIDEO hierarchy.
Excludes internal YouTube IDs and raw text.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChannelOut(BaseModel):
    id: str
    name: str
    channel_url: Optional[str] = None
    description: Optional[str] = None
    subscriber_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProgramOut(BaseModel):
    id: str
    channel_id: str
    channel_name: str
    name: str
    platform: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VideoOut(BaseModel):
    id: str
    program_id: str
    title: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    is_live: bool = False
    comment_count: Optional[int] = None
    scraped_at: datetime

    class Config:
        from_attributes = True
