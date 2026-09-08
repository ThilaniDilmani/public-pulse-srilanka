"""Evidence Pydantic schemas (Phase 11).

Strict Privacy Enforcement:
- NO author_hash
- NO text_raw
- NO PII
- text_clean included only in EvidenceItemOut (justified evidence context)
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class EvidenceRetrievalIn(BaseModel):
    top_k: int = Field(default=20, ge=1, le=100)
    topic: Optional[str] = None
    stance: str = "ALL"
    program_id: Optional[str] = None
    channel_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    keywords: List[str] = Field(default_factory=list)


class EvidenceItemOut(BaseModel):
    rank: int
    evidence_id: str
    comment_id: str
    text_clean: str  # Only clean text exposed in evidence context
    posted_at: Optional[str] = None
    video_id: str
    video_title: Optional[str] = None
    program_name: str
    channel_name: str
    layer2_topic: str
    layer2_confidence: float
    layer4_stance: str
    layer4_confidence: float
    like_count: int
    relevance_score: float
    # author_hash and text_raw strictly excluded!


class EvidencePayloadOut(BaseModel):
    evidence_set_id: str
    retrieved_at: str
    evidence_count: int
    total_matching_count: int
    retrieval_method: str
    evidence_items: List[EvidenceItemOut]
