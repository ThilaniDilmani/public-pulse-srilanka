"""Verification Service orchestrator managing DB persistence for verification results (Phase 10)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from public_pulse.database.repository import insert_verification_result
from public_pulse.evidence.models import EvidencePayload
from public_pulse.insight.models import GeneratedInsight
from public_pulse.verification.config import VerifierConfig
from public_pulse.verification.models import VerificationReport
from public_pulse.verification.verifier import FaithfulnessVerifier

log = logging.getLogger(__name__)


class VerificationService:
    """Orchestrates Phase 10 faithfulness verification and database persistence."""

    def __init__(
        self,
        config: Optional[VerifierConfig] = None,
        verifier: Optional[FaithfulnessVerifier] = None,
    ):
        self.config = config or VerifierConfig()
        self.verifier = verifier or FaithfulnessVerifier(config=self.config)

    def verify_and_persist(
        self,
        db: Session,
        insight: GeneratedInsight,
        payload: EvidencePayload,
        dry_run: bool = False,
    ) -> VerificationReport:
        """Verify insight faithfulness against payload and persist VerificationResult to DB."""
        log.info(
            "Verifying insight_id %s against evidence_set_id %s...",
            insight.insight_id,
            payload.evidence_set_id,
        )

        report = self.verifier.verify(insight, payload)

        if not dry_run:
            db_record = insert_verification_result(
                db,
                insight_id=insight.insight_id,
                evidence_set_id=payload.evidence_set_id,
                verifier_method=report.verifier_method,
                verifier_model=report.verifier_model,
                grounding_score=report.grounding_score,
                claim_support_rate=report.claim_support_rate,
                unsupported_claim_rate=report.unsupported_claim_rate,
                contradiction_rate=report.contradiction_rate,
                verification_details_json=report.to_dict(),
            )
            db.commit()
            log.info(
                "Persisted VerificationResult record %s (CSR=%.2f, CR=%.2f)",
                db_record.id,
                db_record.claim_support_rate,
                db_record.contradiction_rate,
            )

        return report
