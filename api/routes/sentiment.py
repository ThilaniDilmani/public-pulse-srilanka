"""GET /sentiment -- aggregated Layer 4 stance trends.

Stance is the final classification (3 classes: STANCE_CRIT, STANCE_NEUT,
STANCE_SUPP). Sarcasm is not a separate model output -- STANCE_CRIT_SARC
was merged into STANCE_CRIT during data preparation. Do not present
sarcasm as an independent prediction here.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.analytics import StanceDistributionOut
from api.services.analytics_service import AnalyticsService

router = APIRouter(tags=["Analytics"])


@router.get("/sentiment", response_model=StanceDistributionOut)
def get_sentiment(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    topic_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """GET /sentiment -- aggregated Layer 4 stance distribution."""
    return AnalyticsService.get_stance_distribution(
        db,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        topic_filter=topic_filter,
    )
