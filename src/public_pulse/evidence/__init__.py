"""Phase 8 Evidence Extraction & Retrieval package for Public Pulse.

Exported classes:
  - RetrievalConfig: Configuration dataclass for query filters, thresholds, and ranking options.
  - EvidenceItem: Dataclass representing an individual scored YouTube comment evidence item.
  - EvidencePayload: Typed data contract delivered to Phase 9 Grounded LLM.
  - EvidenceRetriever: Main retrieval engine executing Structured Hybrid Retrieval.
"""

from public_pulse.evidence.config import RetrievalConfig
from public_pulse.evidence.models import EvidenceItem, EvidencePayload
from public_pulse.evidence.retriever import EvidenceRetriever

__all__ = [
    "RetrievalConfig",
    "EvidenceItem",
    "EvidencePayload",
    "EvidenceRetriever",
]
