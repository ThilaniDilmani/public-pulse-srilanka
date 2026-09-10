"""Data contract models for Phase 8 evidence items and payload interface to Phase 9."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceItem:
    """An individual scored YouTube comment item packaged as evidence."""

    rank: int
    evidence_id: str
    comment_id: str
    text_raw: str
    text_clean: str
    posted_at: Optional[str]
    video_id: str
    video_title: Optional[str]
    program_name: str
    channel_name: str
    layer2_topic: Optional[str]
    layer2_confidence: Optional[float]
    layer4_stance: Optional[str]
    layer4_confidence: Optional[float]
    like_count: int
    relevance_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence item to dictionary representation."""
        return asdict(self)


@dataclass
class EvidencePayload:
    """Typed data contract delivered to Phase 9 Grounded LLM.

    Phase 9 receives ONLY this payload — no raw SQL/database access is granted.
    """

    evidence_set_id: str
    retrieved_at: str
    retrieval_metadata: Dict[str, Any]
    evidence_count: int
    total_matching_count: int
    retrieval_method: str
    evidence_items: List[EvidenceItem]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize payload to JSON-serializable dictionary."""
        return {
            "evidence_set_id": self.evidence_set_id,
            "retrieved_at": self.retrieved_at,
            "retrieval_metadata": self.retrieval_metadata,
            "evidence_count": self.evidence_count,
            "total_matching_count": self.total_matching_count,
            "retrieval_method": self.retrieval_method,
            "evidence_items": [item.to_dict() for item in self.evidence_items],
        }
