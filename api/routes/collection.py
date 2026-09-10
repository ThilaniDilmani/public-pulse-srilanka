"""Collection API router (Phase 11).

Surfaces endpoints for selecting target channels/programs from catalog,
triggering live data collection jobs, and polling job status.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from api.services.collection_service import CollectionService

router = APIRouter(prefix="/collection", tags=["Collection"])


class CollectionRequest(BaseModel):
    program_names: List[str]
    episodes_per_program: int = 4


@router.get("/catalog")
def get_collection_catalog():
    """Get all available target channels & programs defined in configs/programs.yaml."""
    return CollectionService.get_catalog()


@router.post("/run")
def start_collection_job(req: CollectionRequest):
    """Trigger a live background YouTube data collection and analysis pipeline job."""
    if not req.program_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one program name must be selected.",
        )
    return CollectionService.start_collection(
        program_names=req.program_names,
        episodes_per_program=req.episodes_per_program,
    )


@router.get("/jobs/{job_id}")
def get_collection_job(job_id: str):
    """Check the live status and progress of a background collection job."""
    job = CollectionService.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection job {job_id} not found.",
        )
    return job
