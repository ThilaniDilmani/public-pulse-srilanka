"""Channels catalog endpoints (Phase 11).

Strictly preserves CHANNEL -> PROGRAM -> VIDEO hierarchy.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.catalog import ChannelOut, ProgramOut
from api.services.catalog_service import CatalogService

router = APIRouter(prefix="/channels", tags=["Channels"])


@router.get("", response_model=List[ChannelOut])
def list_channels(db: Session = Depends(get_db)):
    """List all monitored YouTube channels."""
    return CatalogService.get_channels(db)


@router.get("/{channel_id}", response_model=ChannelOut)
def get_channel(channel_id: str, db: Session = Depends(get_db)):
    """Get channel details by channel ID or YouTube channel ID."""
    c = CatalogService.get_channel(db, channel_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return c


@router.get("/{channel_id}/programs", response_model=List[ProgramOut])
def list_channel_programs(channel_id: str, db: Session = Depends(get_db)):
    """List all monitored programs hosted under a specific channel."""
    c = CatalogService.get_channel(db, channel_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return CatalogService.get_programs(db, channel_id=c.id)
