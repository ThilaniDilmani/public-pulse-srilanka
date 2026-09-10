"""Comprehensive analytical endpoints (Phase 11).

Provides maximum-analysis server-side aggregate endpoints:
- KPI overview cards
- Topic breakdowns & Stance breakdowns
- Topic x Stance heatmaps
- Program x Topic / Program x Stance comparison matrices
- Channel x Topic / Channel x Stance comparison matrices
- Volume time-series
- Period-over-period comparisons
- Video/episode analytics
- Pipeline data-quality analytics
- Faithfulness analytics
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.analytics import (
    DataQualityAnalyticsOut,
    EntityMatrixOut,
    FaithfulnessAnalyticsOut,
    OverviewKPIOut,
    PeriodOverPeriodOut,
    StanceDistributionOut,
    TopicDistributionOut,
    TopicStanceMatrixOut,
    VideoAnalyticsOut,
    VolumeOverTimeOut,
)
from api.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=OverviewKPIOut)
def get_analytics_overview(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get overview KPI metrics."""
    return AnalyticsService.get_overview_kpis(
        db,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/topics", response_model=TopicDistributionOut)
def get_topic_distribution(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get Layer 2 macro-topic breakdown."""
    return AnalyticsService.get_topic_distribution(
        db,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/stances", response_model=StanceDistributionOut)
def get_stance_distribution(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    topic_filter: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get Layer 4 stance distribution."""
    return AnalyticsService.get_stance_distribution(
        db,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        topic_filter=topic_filter,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/topic-stance-matrix", response_model=TopicStanceMatrixOut)
def get_topic_stance_matrix(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get Topic x Stance cross-tabulation matrix."""
    return AnalyticsService.get_topic_stance_matrix(
        db,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/entity-matrix", response_model=EntityMatrixOut)
def get_entity_matrix(
    entity_type: str = Query("program", pattern="^(program|channel)$"),
    matrix_type: str = Query("topic", pattern="^(topic|stance)$"),
    channel_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get Program x Topic, Program x Stance, Channel x Topic, or Channel x Stance comparison matrix."""
    return AnalyticsService.get_entity_matrix(
        db,
        entity_type=entity_type,
        matrix_type=matrix_type,
        channel_id=channel_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/volume-over-time", response_model=VolumeOverTimeOut)
def get_volume_over_time(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get volume trend time-series data."""
    return AnalyticsService.get_volume_over_time(
        db,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        granularity=granularity,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/period-over-period", response_model=PeriodOverPeriodOut)
def get_period_over_period(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get period-over-period comparison analytics."""
    return AnalyticsService.get_period_over_period(
        db, program_id=program_id, channel_id=channel_id, period_days=period_days
    )


@router.get("/episodes", response_model=VideoAnalyticsOut)
def get_episode_analytics(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get per-episode/video analytics summary list."""
    return AnalyticsService.get_episode_analytics(
        db, program_id=program_id, channel_id=channel_id, limit=limit, offset=offset
    )


@router.get("/data-quality", response_model=DataQualityAnalyticsOut)
def get_data_quality(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get pipeline data quality and confidence analytics."""
    return AnalyticsService.get_data_quality(
        db,
        program_id=program_id,
        channel_id=channel_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/faithfulness", response_model=FaithfulnessAnalyticsOut)
def get_faithfulness_analytics(
    insight_id: Optional[str] = Query(None),
    program_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get faithfulness verification aggregate metrics."""
    return AnalyticsService.get_faithfulness(db, insight_id=insight_id, program_id=program_id)
