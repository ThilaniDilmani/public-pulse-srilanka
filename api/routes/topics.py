"""GET /topics -- Layer 2 macro-topic breakdowns.

Topic is the final, single-level classification (5 classes: TOPIC_ECON_SERV,
TOPIC_FOR, TOPIC_GOV, TOPIC_LAW, TOPIC_MEDIA). There is no sub-issue layer --
that was Layer 3, which was removed as a documented research-scope decision.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.analytics import TopicDistributionOut
from api.services.analytics_service import AnalyticsService

router = APIRouter(tags=["Analytics"])


@router.get("/topics", response_model=TopicDistributionOut)
def get_topics(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """GET /topics -- Layer 2 macro-topic breakdown."""
    return AnalyticsService.get_topic_distribution(
        db, program_id=program_id, channel_id=channel_id, video_id=video_id
    )
