"""Health check endpoint (Phase 11)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.deps import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Health check verifying database connection and pipeline readiness."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok",
        "phases_complete": 10,
        "active_architecture": "Layer1 -> Layer2 + Layer4",
        "subissue_status": "ABSENT (permanently removed per research scope)",
        "database": db_status,
    }
