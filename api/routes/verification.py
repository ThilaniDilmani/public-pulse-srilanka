"""Faithfulness Verification endpoints (Phase 11).

Async verification via Phase 10 FaithfulnessVerifier.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.insight import JobStatusOut
from api.schemas.verification import VerificationReportOut, VerificationTriggerIn
from api.services.verification_service import VerificationApiService

router = APIRouter(prefix="/insights", tags=["Verification"])


@router.post("/{insight_id}/verify", response_model=JobStatusOut, status_code=status.HTTP_202_ACCEPTED)
def verify_insight(
    insight_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger asynchronous faithfulness verification for a generated insight."""
    try:
        return VerificationApiService.trigger_verification(db, background_tasks, insight_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Verification trigger failed: {e}"
        )


@router.get("/{insight_id}/verification", response_model=VerificationReportOut)
def get_verification_report(insight_id: str, db: Session = Depends(get_db)):
    """Retrieve faithfulness verification report for an insight."""
    report = VerificationApiService.get_verification_report(db, insight_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification report not found for this insight",
        )
    return report
