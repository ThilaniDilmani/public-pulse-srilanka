"""Evidence retrieval endpoint (Phase 11).

Calls Phase 8 EvidenceRetriever synchronously (fast BM25 retrieval).
Strict Privacy:
- Never includes author_hash
- Never includes text_raw
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.deps import get_db
from api.schemas.evidence import EvidencePayloadOut, EvidenceRetrievalIn
from api.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("/retrieve", response_model=EvidencePayloadOut)
def retrieve_evidence(request: EvidenceRetrievalIn, db: Session = Depends(get_db)):
    """Retrieve grounded evidence set from pre-scored comments using BM25 and metadata filters."""
    try:
        return EvidenceService.retrieve_and_persist(db, request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Evidence retrieval failed: {e}"
        )
