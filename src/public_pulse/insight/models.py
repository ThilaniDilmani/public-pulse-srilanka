"""Data contract models for Phase 9 grounded insight generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    """An individual grounded claim or finding linked to supporting evidence IDs."""

    finding_id: str
    text: str
    evidence_ids: List[str]
    confidence: str = "high"  # "high" | "moderate" | "low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary representation."""
        return asdict(self)


@dataclass
class GeneratedInsight:
    """Typed dataclass output produced by GroundedInsightGenerator."""

    insight_id: str
    evidence_set_id: str
    status: str  # "success" | "insufficient_evidence" | "error"
    error_message: Optional[str] = None
    summary: Optional[str] = None
    findings: List[Finding] = field(default_factory=list)
    discourse_interpretation: Optional[str] = None
    limitations: Optional[str] = None
    uncertainty_note: Optional[str] = None
    llm_provider: str = "gemini"
    llm_model: str = "gemini-1.5-flash"
    prompt_version: str = "v1.0"
    generation_params: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_count_used: int = 0
    stance_distribution: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize payload to JSON-serializable dictionary."""
        return {
            "insight_id": self.insight_id,
            "evidence_set_id": self.evidence_set_id,
            "status": self.status,
            "error_message": self.error_message,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "discourse_interpretation": self.discourse_interpretation,
            "limitations": self.limitations,
            "uncertainty_note": self.uncertainty_note,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "prompt_version": self.prompt_version,
            "generation_params": self.generation_params,
            "generated_at": self.generated_at,
            "evidence_count_used": self.evidence_count_used,
            "stance_distribution": self.stance_distribution,
        }
