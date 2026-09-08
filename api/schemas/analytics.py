"""Analytics Pydantic response schemas (Phase 11).

Provides maximum-analysis server-side aggregate schemas for dashboard rendering:
- KPI cards
- Topic & Stance distributions
- Topic x Stance heatmaps
- Entity comparison matrices (Program x Topic, Channel x Stance)
- Volume time-series
- Period-over-period comparison
- Episode/Video analytics
- Data Quality indicators
- Faithfulness indicators
"""

from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel


class OverviewKPIOut(BaseModel):
    total_comments: int
    valid_comments: int
    noise_comments: int
    pending_comments: int
    noise_rate: float
    total_videos: int
    total_programs: int
    total_channels: int
    avg_comments_per_video: float


class TopicDistributionItem(BaseModel):
    topic: str
    count: int
    percentage: float


class TopicDistributionOut(BaseModel):
    program_id: Optional[str] = None
    channel_id: Optional[str] = None
    video_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_valid_comments: int
    distribution: List[TopicDistributionItem]


class StanceDistributionItem(BaseModel):
    stance: str
    count: int
    percentage: float


class StanceDistributionOut(BaseModel):
    program_id: Optional[str] = None
    channel_id: Optional[str] = None
    video_id: Optional[str] = None
    topic_filter: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_valid_comments: int
    distribution: List[StanceDistributionItem]


class TopicStanceMatrixOut(BaseModel):
    program_id: Optional[str] = None
    channel_id: Optional[str] = None
    video_id: Optional[str] = None
    matrix: Dict[str, Dict[str, int]]  # topic -> stance -> count


class EntityMatrixOut(BaseModel):
    entity_type: str  # "program" | "channel"
    matrix_type: str  # "topic" | "stance"
    matrix: Dict[str, Dict[str, int]]  # entity_name -> label -> count


class VolumeDataPoint(BaseModel):
    date: str
    total_comments: int
    valid_comments: int
    noise_comments: int


class VolumeOverTimeOut(BaseModel):
    program_id: Optional[str] = None
    channel_id: Optional[str] = None
    video_id: Optional[str] = None
    granularity: str
    data_points: List[VolumeDataPoint]


class PeriodOverPeriodOut(BaseModel):
    period_days: int
    current_period: Dict
    previous_period: Dict
    changes: Dict


class VideoAnalyticsItem(BaseModel):
    video_id: str
    title: Optional[str] = None
    program_name: str
    published_at: Optional[str] = None
    total_comments: int
    valid_comments: int
    noise_rate: float
    top_topic: Optional[str] = None
    stance_breakdown: Dict[str, int]


class VideoAnalyticsOut(BaseModel):
    items: List[VideoAnalyticsItem]
    total: int


class DataQualityAnalyticsOut(BaseModel):
    overview: Dict
    average_confidence_by_layer: Dict[str, float]
    subissue_status: str


class FaithfulnessAnalyticsOut(BaseModel):
    total_verifications: int
    mean_grounding_score: float
    mean_claim_support_rate: float
    mean_contradiction_rate: float
