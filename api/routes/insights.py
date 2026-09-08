"""Insights endpoints (Phase 11).

Async generation via Phase 9 GroundedInsightGenerator.
Returns 202 Accepted with job reference for polling.
"""

from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.insight import InsightGenerationIn, InsightOut, JobStatusOut
from api.services.insight_service import InsightApiService

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.post("/generate", response_model=JobStatusOut, status_code=status.HTTP_202_ACCEPTED)
def generate_insight(
    request: InsightGenerationIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger asynchronous grounded insight generation from an EvidenceSet."""
    try:
        return InsightApiService.trigger_generation(db, background_tasks, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insight generation trigger failed: {e}"
        )


@router.get("/{insight_id}", response_model=InsightOut)
def get_insight(insight_id: str, db: Session = Depends(get_db)):
    """Retrieve a generated insight by ID."""
    ins = InsightApiService.get_insight(db, insight_id)
    if not ins:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found")
    return ins


@router.get("", response_model=List[InsightOut])
def list_insights(
    program_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    generation_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List generated insights."""
    return InsightApiService.list_insights(
        db, program_id=program_id, limit=limit, offset=offset, generation_status=generation_status
    )
