"""Faithfulness Verification Pydantic schemas (Phase 11)."""

from typing import List, Optional
from pydantic import BaseModel


class VerificationTriggerIn(BaseModel):
    insight_id: str


class ClaimVerificationOut(BaseModel):
    claim_id: str
    finding_id: str
    claim_text: str
    label: str  # "SUPPORTED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED" | "CONTRADICTED"
    evidence_ids: List[str]
    verification_method: str
    reason: str


class VerificationReportOut(BaseModel):
    verification_id: str
    insight_id: str
    evidence_set_id: str
    claim_support_rate: float
    partial_support_rate: float
    unsupported_claim_rate: float
    contradiction_rate: float
    grounding_score: float
    evidence_citation_precision: float
    total_claims_evaluated: int
    claim_verifications: List[ClaimVerificationOut]
    verifier_method: str
    verifier_model: Optional[str] = None
    verified_at: str
