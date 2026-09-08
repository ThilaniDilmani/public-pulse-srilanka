"""Comments analytics endpoint (Phase 11).

Strict Privacy Enforcement:
- Never exposes author_hash or usernames
- Never exposes text_raw
- General comment endpoints do not return raw text
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.analytics import OverviewKPIOut
from api.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/comments", tags=["Comments"])


@router.get("/summary", response_model=OverviewKPIOut)
def get_comments_summary(
    program_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get aggregated comment volume and scoring status summary (privacy-safe)."""
    return AnalyticsService.get_overview_kpis(
        db, program_id=program_id, channel_id=channel_id, video_id=video_id
    )
