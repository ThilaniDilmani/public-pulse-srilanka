"""Programs endpoints (Phase 11).

Strictly preserves CHANNEL -> PROGRAM -> VIDEO -> COMMENT hierarchy.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.catalog import ProgramOut, VideoOut
from api.schemas.insight import InsightOut
from api.schemas.analytics import (
    OverviewKPIOut,
    StanceDistributionOut,
    TopicDistributionOut,
    TopicStanceMatrixOut,
    VolumeOverTimeOut,
)
from api.services.catalog_service import CatalogService
from api.services.analytics_service import AnalyticsService
from api.services.insight_service import InsightApiService

router = APIRouter(prefix="/programs", tags=["Programs"])


@router.get("", response_model=List[ProgramOut])
def list_programs(
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
):
    """List monitored programs with channel context."""
    return CatalogService.get_programs(db, channel_id=channel_id, is_active=is_active)


@router.get("/{program_id}", response_model=ProgramOut)
def get_program(program_id: str, db: Session = Depends(get_db)):
    """Get program details by program ID."""
    p = CatalogService.get_program(db, program_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return p


@router.get("/{program_id}/videos", response_model=List[VideoOut])
def list_program_videos(
    program_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List videos/episodes belonging to a program."""
    p = CatalogService.get_program(db, program_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return CatalogService.get_videos_for_program(db, program_id, limit=limit, offset=offset)


@router.get("/{program_id}/analytics/overview", response_model=OverviewKPIOut)
def get_program_analytics_overview(
    program_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get overview KPIs for a specific program."""
    p = CatalogService.get_program(db, program_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return AnalyticsService.get_overview_kpis(
        db, program_id=program_id, start_date=start_date, end_date=end_date
    )


@router.get("/{program_id}/analytics/topics", response_model=TopicDistributionOut)
def get_program_topic_distribution(
    program_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get Layer 2 macro-topic breakdown for a specific program."""
    p = CatalogService.get_program(db, program_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return AnalyticsService.get_topic_distribution(
        db, program_id=program_id, start_date=start_date, end_date=end_date
    )


@router.get("/{program_id}/analytics/stances", response_model=StanceDistributionOut)
def get_program_stance_distribution(
    program_id: str,
    topic: Optional[str] = Query(None, description="Filter by macro-topic"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get Layer 4 stance distribution for a specific program."""
    p = CatalogService.get_program(db, program_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return AnalyticsService.get_stance_distribution(
        db, program_id=program_id, topic_filter=topic, start_date=start_date, end_date=end_date
    )


@router.get("/{program_id}/analytics/topic-stance-matrix", response_model=TopicStanceMatrixOut)
def get_program_topic_stance_matrix(
    program_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get Topic x Stance matrix for a specific program."""
    p = CatalogService.get_program(db, program_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return AnalyticsService.get_topic_stance_matrix(
        db, program_id=program_id, start_date=start_date, end_date=end_date
    )


@router.get("/{program_id}/analytics/volume-over-time", response_model=VolumeOverTimeOut)
def get_program_volume_over_time(
    program_id: str,
    granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get comment volume trend time series for a program."""
    p = CatalogService.get_program(db, program_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return AnalyticsService.get_volume_over_time(
        db, program_id=program_id, granularity=granularity, start_date=start_date, end_date=end_date
    )


@router.get("/{program_id}/insights", response_model=List[InsightOut])
def list_program_insights(
    program_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List generated insights for a program."""
    p = CatalogService.get_program(db, program_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return InsightApiService.list_insights(db, program_id=program_id, limit=limit, offset=offset)
