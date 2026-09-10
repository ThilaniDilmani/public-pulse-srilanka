"""Configuration dataclass for Phase 8 evidence extraction and retrieval.

Provides parameters for metadata filtering, confidence thresholds, BM25 scoring,
near-duplicate filtering, source diversity, multi-stance allocation, and reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class RetrievalConfig:
    """Configurable parameters for evidence extraction and retrieval.

    Confidence thresholds are quality heuristics and remain fully configurable.
    """

    top_k: int = 20
    topic: Optional[str] = None  # e.g., "TOPIC_ECON_SERV" or None for all topics
    stance: str = "ALL"  # "STANCE_CRIT", "STANCE_NEUT", "STANCE_SUPP", or "ALL"
    program_id: Optional[str] = None
    channel_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    keywords: List[str] = field(default_factory=list)

    # Quality & Confidence Thresholds (configurable heuristics)
    min_layer1_confidence: float = 0.50
    min_layer2_confidence: float = 0.70
    min_layer4_confidence: float = 0.70
    min_clean_text_length: int = 10
    min_word_count: int = 3

    # Diversity & Deduplication parameters
    max_per_video: int = 2
    near_duplicate_threshold: float = 0.85

    # Provenance
    retrieval_method: str = "hybrid_bm25_v1"

    def to_dict(self) -> dict:
        """Serialize configuration to a structured dictionary for query provenance."""
        return {
            "top_k": self.top_k,
            "topic": self.topic,
            "stance": self.stance,
            "program_id": self.program_id,
            "channel_id": self.channel_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "keywords": self.keywords,
            "confidence_thresholds": {
                "layer1": self.min_layer1_confidence,
                "layer2": self.min_layer2_confidence,
                "layer4": self.min_layer4_confidence,
            },
            "quality_filters": {
                "min_clean_text_length": self.min_clean_text_length,
                "min_word_count": self.min_word_count,
            },
            "diversity_config": {
                "max_per_video": self.max_per_video,
                "near_duplicate_threshold": self.near_duplicate_threshold,
            },
            "retrieval_method": self.retrieval_method,
        }
