"""Verification API service connecting REST endpoints to Phase 10 Faithfulness Verifier (Phase 11).

Verification executes asynchronously via background tasks.
"""

from typing import Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from public_pulse.database import repository
from public_pulse.verification.service import VerificationService as Phase10VerificationService
from api.schemas.insight import JobStatusOut
from api.schemas.verification import ClaimVerificationOut, VerificationReportOut
from api.services.job_service import JobService
from api.deps import SessionLocal


def _bg_verify_insight(job_id: str, insight_id: str):
    """Background task function for running faithfulness verification."""
    db = SessionLocal()
    try:
        JobService.update_job(db, job_id, status="running")

        ins = repository.get_insight(db, insight_id)
        if not ins:
            JobService.update_job(db, job_id, status="error", error="Insight not found")
            return

        if not ins.evidence_set_id:
            JobService.update_job(db, job_id, status="error", error="Insight has no linked EvidenceSet")
            return

        p10_service = Phase10VerificationService()
        report = p10_service.verify_and_persist(db, str(ins.id), str(ins.evidence_set_id))

        JobService.update_job(db, job_id, status="completed", reference_id=report.verification_id)
    except Exception as e:
        JobService.update_job(db, job_id, status="error", error=str(e))
    finally:
        db.close()


class VerificationApiService:

    @staticmethod
    def trigger_verification(
        db: Session,
        background_tasks: BackgroundTasks,
        insight_id: str,
    ) -> JobStatusOut:
        ins = repository.get_insight(db, insight_id)
        if not ins:
            raise ValueError(f"Insight {insight_id} not found")

        # Check if verification already exists for default method
        existing = repository.get_verification_result(db, insight_id)
        if existing:
            # Already verified
            return JobStatusOut(
                job_id=str(existing.id),
                job_type="faithfulness_verification",
                status="completed",
                reference_id=str(existing.id),
                created_at=existing.verified_at.isoformat(),
                completed_at=existing.verified_at.isoformat(),
            )

        job = JobService.create_job(db, job_type="faithfulness_verification", reference_id=insight_id)
        background_tasks.add_task(_bg_verify_insight, job.job_id, insight_id)
        return job

    @staticmethod
    def get_verification_report(db: Session, insight_id: str) -> Optional[VerificationReportOut]:
        vres = repository.get_verification_result(db, insight_id)
        if not vres:
            return None

        details = vres.verification_details_json or {}
        claims_data = details.get("claim_verifications", [])
        claims = [
            ClaimVerificationOut(
                claim_id=c.get("claim_id", ""),
                finding_id=c.get("finding_id", ""),
                claim_text=c.get("claim_text", ""),
                label=c.get("label", "UNSUPPORTED"),
                evidence_ids=c.get("evidence_ids", []),
                verification_method=c.get("verification_method", "heuristic"),
                reason=c.get("reason", ""),
            )
            for c in claims_data
        ]

        return VerificationReportOut(
            verification_id=str(vres.id),
            insight_id=str(vres.insight_id),
            evidence_set_id=str(vres.evidence_set_id),
            claim_support_rate=vres.claim_support_rate,
            partial_support_rate=details.get("partial_support_rate", 0.0),
            unsupported_claim_rate=vres.unsupported_claim_rate,
            contradiction_rate=vres.contradiction_rate,
            grounding_score=vres.grounding_score,
            evidence_citation_precision=details.get("evidence_citation_precision", 0.0),
            total_claims_evaluated=details.get("total_claims_evaluated", len(claims)),
            claim_verifications=claims,
            verifier_method=vres.verifier_method,
            verifier_model=vres.verifier_model,
            verified_at=vres.verified_at.isoformat(),
        )
