"""Core Grounded Insight Generator for Phase 9.

CRITICAL INVARIANT:
This class has ZERO direct database access. It does NOT import SQLAlchemy, Session,
or ORM repositories. It operates purely on EvidencePayload and returns GeneratedInsight.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from public_pulse.evidence.models import EvidencePayload
from public_pulse.insight.config import InsightGeneratorConfig
from public_pulse.insight.models import Finding, GeneratedInsight
from public_pulse.insight.prompt import build_prompt
from public_pulse.insight.provider import GeminiProvider, LLMProvider, MockLLMProvider

log = logging.getLogger(__name__)

# Prohibited population-level claim phrases
PROHIBITED_UNBOUNDED_PATTERNS = [
    r"\bsri lankans believe\b",
    r"\bthe sri lankan public wants\b",
    r"\beveryone agrees\b",
    r"\ball voters\b",
    r"\bthe population supports\b",
]


class GroundedInsightGenerator:
    """Core LLM insight generator producing grounded insights from EvidencePayload."""

    def __init__(
        self,
        config: Optional[InsightGeneratorConfig] = None,
        provider: Optional[LLMProvider] = None,
    ):
        self.config = config or InsightGeneratorConfig()
        if provider is not None:
            self.provider = provider
        elif self.config.llm_provider == "mock":
            self.provider = MockLLMProvider()
        else:
            self.provider = GeminiProvider(
                model_name=self.config.llm_model,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
                timeout_seconds=self.config.timeout_seconds,
                max_retries=self.config.max_retries,
                retry_delay_seconds=self.config.retry_delay_seconds,
            )

    def generate(self, payload: EvidencePayload) -> GeneratedInsight:
        """Generate a typed, grounded insight from an EvidencePayload."""
        insight_id = str(uuid.uuid4())

        # 1. Compute quantitative stance distribution from payload
        stance_counts: Dict[str, int] = {}
        for item in payload.evidence_items:
            st = item.layer4_stance or "UNKNOWN"
            stance_counts[st] = stance_counts.get(st, 0) + 1

        total_items = max(payload.evidence_count, 1)
        stance_dist = {st: round(count / total_items, 4) for st, count in stance_counts.items()}

        # 2. Check minimum evidence threshold (Zero LLM call if below threshold)
        if payload.evidence_count < self.config.min_evidence_threshold:
            log.info(
                "Evidence count (%d) below threshold (%d); returning status='insufficient_evidence'.",
                payload.evidence_count,
                self.config.min_evidence_threshold,
            )
            return GeneratedInsight(
                insight_id=insight_id,
                evidence_set_id=payload.evidence_set_id,
                status="insufficient_evidence",
                error_message=None,
                summary=None,
                findings=[],
                discourse_interpretation=None,
                limitations=(
                    f"Retrieved evidence count ({payload.evidence_count}) is below the required "
                    f"minimum threshold ({self.config.min_evidence_threshold}) for grounded insight generation."
                ),
                uncertainty_note="Insufficient evidence to draw reliable interpretations.",
                llm_provider=self.config.llm_provider,
                llm_model=self.config.llm_model,
                prompt_version=self.config.prompt_version,
                generation_params=self.config.to_dict(),
                generated_at=datetime.now(timezone.utc).isoformat(),
                evidence_count_used=payload.evidence_count,
                stance_distribution=stance_dist,
            )

        # 3. Construct prompt tuple (system_instructions, user_prompt)
        sys_prompt, user_prompt = build_prompt(payload, version=self.config.prompt_version)

        # 4. Invoke LLM provider with error safety
        try:
            raw_response = self.provider.generate(sys_prompt, user_prompt)
        except Exception as exc:
            log.exception("LLM generation failed: %s", exc)
            return GeneratedInsight(
                insight_id=insight_id,
                evidence_set_id=payload.evidence_set_id,
                status="error",
                error_message=f"LLM API call failed: {exc}",
                summary=None,
                findings=[],
                discourse_interpretation=None,
                limitations="Generation aborted due to LLM provider failure.",
                uncertainty_note=None,
                llm_provider=self.config.llm_provider,
                llm_model=self.config.llm_model,
                prompt_version=self.config.prompt_version,
                generation_params=self.config.to_dict(),
                generated_at=datetime.now(timezone.utc).isoformat(),
                evidence_count_used=payload.evidence_count,
                stance_distribution=stance_dist,
            )

        # 5. Parse JSON response
        try:
            # Strip markdown codeblocks if present
            clean_json = raw_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\n", "", clean_json)
                clean_json = re.sub(r"\n```$", "", clean_json)

            data = json.loads(clean_json)
        except Exception as exc:
            log.error("Failed to parse LLM response as JSON: %s. Raw: %r", exc, raw_response)
            return GeneratedInsight(
                insight_id=insight_id,
                evidence_set_id=payload.evidence_set_id,
                status="error",
                error_message=f"Malformed LLM JSON output: {exc}",
                summary=None,
                findings=[],
                discourse_interpretation=None,
                limitations="Generation failed due to non-parseable JSON response.",
                uncertainty_note=None,
                llm_provider=self.config.llm_provider,
                llm_model=self.config.llm_model,
                prompt_version=self.config.prompt_version,
                generation_params=self.config.to_dict(),
                generated_at=datetime.now(timezone.utc).isoformat(),
                evidence_count_used=payload.evidence_count,
                stance_distribution=stance_dist,
            )

        # 6. Validate findings & evidence traceability
        valid_evidence_ids: Set[str] = {item.evidence_id for item in payload.evidence_items}
        raw_findings = data.get("findings", [])
        validated_findings: List[Finding] = []
        unsupported_count = 0

        for f_idx, f_raw in enumerate(raw_findings, start=1):
            if not isinstance(f_raw, dict):
                continue
            text = f_raw.get("text", "")
            e_ids = f_raw.get("evidence_ids", [])
            confidence = f_raw.get("confidence", "high")

            # Filter evidence_ids to only those present in payload
            filtered_e_ids = [eid for eid in e_ids if str(eid) in valid_evidence_ids]
            if len(filtered_e_ids) < len(e_ids):
                unsupported_count += (len(e_ids) - len(filtered_e_ids))

            # Bounded language check: replace or flag prohibited population-level phrases
            for pattern in PROHIBITED_UNBOUNDED_PATTERNS:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    text = re.sub(pattern, "retrieved comments indicate", text, flags=re.IGNORECASE)

            validated_findings.append(
                Finding(
                    finding_id=f_raw.get("finding_id", f"F{f_idx}"),
                    text=text,
                    evidence_ids=filtered_e_ids,
                    confidence=confidence,
                )
            )

        limitations = data.get("limitations", "")
        if unsupported_count > 0:
            limitations += f" Note: {unsupported_count} invalid evidence ID reference(s) were filtered out during validation."

        status_flag = data.get("status", "success")
        if status_flag not in ("success", "insufficient_evidence", "error"):
            status_flag = "success"

        return GeneratedInsight(
            insight_id=insight_id,
            evidence_set_id=payload.evidence_set_id,
            status=status_flag,
            error_message=None,
            summary=data.get("summary"),
            findings=validated_findings,
            discourse_interpretation=data.get("discourse_interpretation"),
            limitations=limitations or None,
            uncertainty_note=data.get("uncertainty_note"),
            llm_provider=self.config.llm_provider,
            llm_model=self.config.llm_model,
            prompt_version=self.config.prompt_version,
            generation_params=self.config.to_dict(),
            generated_at=datetime.now(timezone.utc).isoformat(),
            evidence_count_used=payload.evidence_count,
            stance_distribution=stance_dist,
        )
