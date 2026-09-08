"""Evidence service interfacing with Phase 8 EvidenceRetriever (Phase 11).

Ensures Privacy:
- Never includes author_hash
- Never includes text_raw
"""

import uuid as uuid_mod
from sqlalchemy.orm import Session
from public_pulse.database import repository
from public_pulse.evidence.config import RetrievalConfig
from public_pulse.evidence.retriever import EvidenceRetriever
from api.schemas.evidence import EvidenceItemOut, EvidencePayloadOut, EvidenceRetrievalIn


class EvidenceService:

    @staticmethod
    def retrieve_and_persist(db: Session, request: EvidenceRetrievalIn) -> EvidencePayloadOut:
        config = RetrievalConfig(
            top_k=request.top_k,
            topic=request.topic,
            stance=request.stance,
            program_id=request.program_id,
            channel_id=request.channel_id,
            start_date=request.start_date,
            end_date=request.end_date,
            keywords=request.keywords,
        )

        retriever = EvidenceRetriever(config=config)
        payload = retriever.retrieve(db)

        # Persist EvidenceSet to DB
        ev_set = repository.insert_evidence_set(
            db,
            query_params=payload.retrieval_metadata,
            retrieval_method=payload.retrieval_method,
            items=[
                {
                    "comment_id": uuid_mod.UUID(item.comment_id) if isinstance(item.comment_id, str) else item.comment_id,
                    "evidence_type": "bm25_retrieved",
                    "layer": "layer2",
                    "label": item.layer2_topic,
                    "confidence": item.layer2_confidence,
                    "relevance_score": item.relevance_score,
                    "rank": item.rank,
                }
                for item in payload.evidence_items
            ],
        )

        # Map to Pydantic schema (strictly excluding author_hash and text_raw)
        items_out = [
            EvidenceItemOut(
                rank=item.rank,
                evidence_id=item.evidence_id,
                comment_id=item.comment_id,
                text_clean=item.text_clean,
                posted_at=item.posted_at,
                video_id=item.video_id,
                video_title=item.video_title,
                program_name=item.program_name,
                channel_name=item.channel_name,
                layer2_topic=item.layer2_topic,
                layer2_confidence=item.layer2_confidence,
                layer4_stance=item.layer4_stance,
                layer4_confidence=item.layer4_confidence,
                like_count=item.like_count,
                relevance_score=item.relevance_score,
            )
            for item in payload.evidence_items
        ]

        return EvidencePayloadOut(
            evidence_set_id=str(ev_set.id),
            retrieved_at=payload.retrieved_at,
            evidence_count=payload.evidence_count,
            total_matching_count=payload.total_matching_count,
            retrieval_method=payload.retrieval_method,
            evidence_items=items_out,
        )
