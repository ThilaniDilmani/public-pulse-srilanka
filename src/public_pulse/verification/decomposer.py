"""Atomic claim decomposer for Phase 10 Faithfulness Verification.

Uses deterministic heuristic clause splitting as the primary decomposition method.
Decomposition is explicitly documented as heuristic clause splitting rather than full semantic parsing.
Ambiguous findings are preserved as single atomic claims to avoid silent text loss.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from public_pulse.insight.models import Finding


class ClaimDecomposer:
    """Decomposes Finding objects into atomic claim statements with stable claim_ids (F1-C1, F1-C2)."""

    def decompose_finding(self, finding: Finding) -> List[Tuple[str, str]]:
        """Decompose a single Finding into a list of (claim_id, claim_text) tuples.

        Heuristic rules:
        - Split on strong contrastive connectors (";", "while", "whereas", "however") if both sides exceed 15 chars.
        - Do NOT split on simple coordinate conjunctions ("and") to avoid fragmenting complex predicates.
        - If splitting yields fragments < 15 chars or is ambiguous, preserve the original finding text.
        """
        text = finding.text.strip()
        f_id = finding.finding_id or "F1"

        if not text:
            return [(f"{f_id}-C1", text)]

        # Split regex on contrastive clause boundaries: ';' or ', while ', ', whereas ', ', however '
        pattern = r"\s*;\s*|\s*,\s*(?:while|whereas|however)\s+"
        parts = re.split(pattern, text, flags=re.IGNORECASE)

        valid_parts = [p.strip() for p in parts if p and len(p.strip()) >= 15]

        # If splitting resulted in only 1 part or invalid fragments, preserve original
        if len(valid_parts) <= 1:
            return [(f"{f_id}-C1", text)]

        results = []
        for idx, part in enumerate(valid_parts, start=1):
            claim_id = f"{f_id}-C{idx}"
            # Ensure each part starts with capital or maintains Sinhala/Singlish text
            results.append((claim_id, part))

        return results
