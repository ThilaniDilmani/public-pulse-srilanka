"""Deterministic Stage 1 checkers for Phase 10 Faithfulness Verification.

Implements rule-based checks for:
  - Citation integrity & invalid evidence ID validation
  - Population-level overgeneralization detection
  - Structured numerical and percentage claim verification
  - Quantifier policy heuristics (most, majority, minority, few, half, all)
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from public_pulse.evidence.models import EvidencePayload
from public_pulse.verification.models import ClaimVerification

PROHIBITED_UNBOUNDED_PATTERNS = [
    r"\bsri lankans believe\b",
    r"\bthe sri lankan public wants\b",
    r"\beveryone agrees\b",
    r"\ball voters\b",
    r"\bthe population supports\b",
]

# Quantifier policy heuristic thresholds (documented as heuristic interpretations, not exact math)
QUANTIFIER_THRESHOLDS = {
    "majority": 0.50,         # >= 50% of retrieved evidence
    "most": 0.50,             # >= 50%
    "minority": 0.50,         # < 50%
    "few": 0.30,              # < 30%
    "half_min": 0.40,         # 40% - 60%
    "half_max": 0.60,
    "all": 0.95,              # >= 95%
}


class DeterministicChecker:
    """Stage 1 deterministic rule checker evaluating claims against metadata and policies."""

    def __init__(self, numerical_tolerance: float = 0.15):
        self.numerical_tolerance = numerical_tolerance

    def check_citation_integrity(
        self,
        claim_id: str,
        finding_id: str,
        claim_text: str,
        evidence_ids: List[str],
        payload: EvidencePayload,
    ) -> Optional[ClaimVerification]:
        """Check citation validity. Returns ClaimVerification if rule triggers, else None."""
        if not evidence_ids:
            return ClaimVerification(
                claim_id=claim_id,
                finding_id=finding_id,
                claim_text=claim_text,
                label="UNSUPPORTED",
                evidence_ids=[],
                verification_method="rule_citation",
                reason="Claim contains no cited evidence IDs.",
            )

        payload_ids: Set[str] = {item.evidence_id for item in payload.evidence_items}
        valid_ids = [eid for eid in evidence_ids if str(eid) in payload_ids]

        if not valid_ids:
            return ClaimVerification(
                claim_id=claim_id,
                finding_id=finding_id,
                claim_text=claim_text,
                label="UNSUPPORTED",
                evidence_ids=[],
                verification_method="rule_citation",
                reason="All cited evidence IDs are invalid or outside the supplied EvidencePayload.",
            )

        return None

    def check_overgeneralization(
        self,
        claim_id: str,
        finding_id: str,
        claim_text: str,
        evidence_ids: List[str],
    ) -> Optional[ClaimVerification]:
        """Check for population-level overclaims. Returns ClaimVerification if rule triggers, else None."""
        # Exception: explicit sample qualifier present
        if "among the analyzed" in claim_text.lower() or "within the retrieved" in claim_text.lower():
            return None

        for pattern in PROHIBITED_UNBOUNDED_PATTERNS:
            if re.search(pattern, claim_text, flags=re.IGNORECASE):
                return ClaimVerification(
                    claim_id=claim_id,
                    finding_id=finding_id,
                    claim_text=claim_text,
                    label="UNSUPPORTED",
                    evidence_ids=evidence_ids,
                    verification_method="rule_overgeneralization",
                    reason=f"Claim asserts population-level overgeneralization matching pattern '{pattern}'.",
                )

        return None

    def check_numerical_and_quantifiers(
        self,
        claim_id: str,
        finding_id: str,
        claim_text: str,
        evidence_ids: List[str],
        payload: EvidencePayload,
    ) -> Optional[ClaimVerification]:
        """Check percentage, ratio, and quantifier claims against actual payload stance metadata."""
        if not payload.evidence_items:
            return None

        # Compute actual stance ratios from payload evidence items
        total_items = len(payload.evidence_items)
        crit_count = sum(1 for item in payload.evidence_items if item.layer4_stance == "STANCE_CRIT")
        supp_count = sum(1 for item in payload.evidence_items if item.layer4_stance == "STANCE_SUPP")
        neut_count = sum(1 for item in payload.evidence_items if item.layer4_stance == "STANCE_NEUT")

        actual_crit_ratio = crit_count / total_items
        actual_supp_ratio = supp_count / total_items

        # 1. Percentage check (e.g. "60% of comments were critical" or "50% were critical")
        pct_match = re.search(r"(\d+)\s*%\s*.*?\b(critical|supportive|neutral)\b", claim_text, re.IGNORECASE)
        if pct_match:
            claimed_pct = float(pct_match.group(1)) / 100.0
            stance_type = pct_match.group(2).lower()
            actual_ratio = actual_crit_ratio if "crit" in stance_type else (actual_supp_ratio if "supp" in stance_type else (neut_count / total_items))

            if abs(claimed_pct - actual_ratio) <= self.numerical_tolerance:
                return ClaimVerification(
                    claim_id=claim_id,
                    finding_id=finding_id,
                    claim_text=claim_text,
                    label="SUPPORTED",
                    evidence_ids=evidence_ids,
                    verification_method="rule_numerical",
                    reason=f"Claimed percentage ({claimed_pct:.0%}) matches actual payload ratio ({actual_ratio:.0%}) within tolerance.",
                )
            else:
                return ClaimVerification(
                    claim_id=claim_id,
                    finding_id=finding_id,
                    claim_text=claim_text,
                    label="CONTRADICTED",
                    evidence_ids=evidence_ids,
                    verification_method="rule_numerical",
                    reason=f"Claimed percentage ({claimed_pct:.0%}) contradicts actual payload ratio ({actual_ratio:.0%}).",
                )

        # 2. Quantifier policy checks (majority, most, minority, few, half, all)
        text_lower = claim_text.lower()
        if "majority" in text_lower or "most" in text_lower:
            if "critical" in text_lower:
                if actual_crit_ratio >= QUANTIFIER_THRESHOLDS["majority"]:
                    return ClaimVerification(
                        claim_id=claim_id,
                        finding_id=finding_id,
                        claim_text=claim_text,
                        label="SUPPORTED",
                        evidence_ids=evidence_ids,
                        verification_method="rule_quantifier",
                        reason=f"Claim asserts majority/most critical; actual critical stance ratio is {actual_crit_ratio:.0%}.",
                    )
                else:
                    return ClaimVerification(
                        claim_id=claim_id,
                        finding_id=finding_id,
                        claim_text=claim_text,
                        label="CONTRADICTED",
                        evidence_ids=evidence_ids,
                        verification_method="rule_quantifier",
                        reason=f"Claim asserts majority/most critical, but actual critical stance ratio is {actual_crit_ratio:.0%}.",
                    )
            elif "supportive" in text_lower:
                if actual_supp_ratio >= QUANTIFIER_THRESHOLDS["majority"]:
                    return ClaimVerification(
                        claim_id=claim_id,
                        finding_id=finding_id,
                        claim_text=claim_text,
                        label="SUPPORTED",
                        evidence_ids=evidence_ids,
                        verification_method="rule_quantifier",
                        reason=f"Claim asserts majority/most supportive; actual supportive stance ratio is {actual_supp_ratio:.0%}.",
                    )
                else:
                    return ClaimVerification(
                        claim_id=claim_id,
                        finding_id=finding_id,
                        claim_text=claim_text,
                        label="CONTRADICTED",
                        evidence_ids=evidence_ids,
                        verification_method="rule_quantifier",
                        reason=f"Claim asserts majority/most supportive, but actual supportive stance ratio is {actual_supp_ratio:.0%}.",
                    )

        if "minority" in text_lower or "few" in text_lower:
            if "critical" in text_lower and actual_crit_ratio >= QUANTIFIER_THRESHOLDS["majority"]:
                return ClaimVerification(
                    claim_id=claim_id,
                    finding_id=finding_id,
                    claim_text=claim_text,
                    label="CONTRADICTED",
                    evidence_ids=evidence_ids,
                    verification_method="rule_quantifier",
                    reason=f"Claim asserts minority/few critical, but actual critical stance ratio is {actual_crit_ratio:.0%}.",
                )

        return None
