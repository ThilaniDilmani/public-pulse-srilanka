"""Data contract models for Phase 10 Faithfulness Verification."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ClaimVerification:
    """Verification result for an individual atomic claim."""

    claim_id: str                 # e.g., "F1-C1"
    finding_id: str               # e.g., "F1"
    claim_text: str               # Atomic claim statement
    label: str                    # "SUPPORTED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED" | "CONTRADICTED"
    evidence_ids: List[str]       # Valid cited evidence IDs
    verification_method: str      # "rule_citation" | "rule_numerical" | "rule_overgeneralization" | "llm_nli"
    reason: str                   # Human-readable justification

    def to_dict(self) -> Dict[str, Any]:
        """Convert claim verification to dictionary representation."""
        return asdict(self)


@dataclass
class VerificationReport:
    """Complete verification evaluation report for a GeneratedInsight."""

    verification_id: str
    insight_id: str
    evidence_set_id: str
    verifier_method: str
    verifier_model: str
    claim_support_rate: float            # CSR = SUPPORTED / total
    partial_support_rate: float          # PSR = PARTIALLY_SUPPORTED / total
    unsupported_claim_rate: float        # UCR = UNSUPPORTED / total
    contradiction_rate: float            # CR = CONTRADICTED / total
    grounding_score: float               # Secondary heuristic G = CSR + 0.5 * PSR
    evidence_citation_precision: float   # Precision of evidence ID references
    total_claims_evaluated: int
    claim_verifications: List[ClaimVerification] = field(default_factory=list)
    verified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to JSON-serializable dictionary."""
        return {
            "verification_id": self.verification_id,
            "insight_id": self.insight_id,
            "evidence_set_id": self.evidence_set_id,
            "verifier_method": self.verifier_method,
            "verifier_model": self.verifier_model,
            "claim_support_rate": round(self.claim_support_rate, 4),
            "partial_support_rate": round(self.partial_support_rate, 4),
            "unsupported_claim_rate": round(self.unsupported_claim_rate, 4),
            "contradiction_rate": round(self.contradiction_rate, 4),
            "grounding_score": round(self.grounding_score, 4),
            "evidence_citation_precision": round(self.evidence_citation_precision, 4),
            "total_claims_evaluated": self.total_claims_evaluated,
            "claim_verifications": [cv.to_dict() for cv in self.claim_verifications],
            "verified_at": self.verified_at,
        }
