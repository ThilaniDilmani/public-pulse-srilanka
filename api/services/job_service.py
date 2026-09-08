"""Job management service for async background operations (Phase 11)."""

from typing import Optional
from sqlalchemy.orm import Session
from public_pulse.database import repository
from api.schemas.insight import JobStatusOut


class JobService:

    @staticmethod
    def create_job(db: Session, job_type: str, reference_id: Optional[str] = None) -> JobStatusOut:
        job = repository.create_job(db, job_type=job_type, reference_id=reference_id)
        db.commit()
        return JobStatusOut(
            job_id=str(job.id),
            job_type=job.job_type,
            status=job.status,
            reference_id=job.reference_id,
            error=job.error,
            created_at=job.created_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )

    @staticmethod
    def get_job_status(db: Session, job_id: str) -> Optional[JobStatusOut]:
        job = repository.get_job(db, job_id)
        if not job:
            return None
        return JobStatusOut(
            job_id=str(job.id),
            job_type=job.job_type,
            status=job.status,
            reference_id=job.reference_id,
            error=job.error,
            created_at=job.created_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )

    @staticmethod
    def update_job(
        db: Session,
        job_id: str,
        status: str,
        reference_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        repository.update_job_status(db, job_id, status=status, reference_id=reference_id, error=error)
        db.commit()
