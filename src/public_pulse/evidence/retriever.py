"""Core evidence retriever engine for Phase 8.

Implements Structured Hybrid Retrieval:
  1. Eligibility & quality filtering (scored/VALID only, text substance)
  2. Metadata filtering (program, channel, date window)
  3. Layer 2 topic and Layer 4 stance constraints
  4. Candidate pool construction & BM25 lexical relevance scoring
  5. Exact & near-duplicate removal (text-based only; zero user profiling)
  6. Deterministic multi-key tie-breaking (relevance_score DESC, posted_at DESC, like_count DESC, comment_id ASC)
  7. Source/video diversity capping (max comments per video)
  8. Proportional multi-stance allocation (when stance='ALL')
  9. Top-K evidence selection
 10. Idempotent persistence of EvidenceSet and Evidence records
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from public_pulse.database.models import (
    Comment,
    Evidence,
    EvidenceSet,
    LayerEnum,
    LayerPrediction,
    ProcessingStatusEnum,
    Program,
    Video,
)
from public_pulse.database.repository import insert_evidence_set
from public_pulse.evidence.config import RetrievalConfig
from public_pulse.evidence.models import EvidenceItem, EvidencePayload


def _tokenize(text: str) -> List[str]:
    """Simple whitespace and punctuation tokenizer supporting Sinhala, English, and Singlish."""
    if not text:
        return []
    text_clean = re.sub(r"[^\w\s\u0D80-\u0DFF]", " ", text.lower())
    return [t for t in text_clean.split() if t]


def _jaccard_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """Compute Jaccard similarity between two lists of word tokens."""
    set1, set2 = set(tokens1), set(tokens2)
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / float(union) if union > 0 else 0.0


def _compute_bm25_scores(texts: List[str], keywords: List[str], k1: float = 1.5, b: float = 0.75) -> List[float]:
    """Compute lightweight BM25 lexical relevance scores for texts against query keywords."""
    if not keywords:
        return [1.0 for _ in texts]

    tokenized_docs = [_tokenize(t) for t in texts]
    tokenized_query = []
    for kw in keywords:
        tokenized_query.extend(_tokenize(kw))

    if not tokenized_query or not tokenized_docs:
        return [0.0 for _ in texts]

    doc_lengths = [len(doc) for doc in tokenized_docs]
    avg_doc_len = sum(doc_lengths) / max(len(doc_lengths), 1)
    num_docs = len(tokenized_docs)

    # Document frequency
    df: Dict[str, int] = {}
    for q_term in tokenized_query:
        df[q_term] = sum(1 for doc in tokenized_docs if q_term in doc)

    # IDF per query term
    idf: Dict[str, float] = {}
    for q_term, doc_freq in df.items():
        # Standard BM25 IDF formula
        idf[q_term] = math.log((num_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)

    scores = []
    for doc, d_len in zip(tokenized_docs, doc_lengths):
        score = 0.0
        doc_term_counts: Dict[str, int] = {}
        for term in doc:
            doc_term_counts[term] = doc_term_counts.get(term, 0) + 1

        for q_term in tokenized_query:
            if q_term in doc_term_counts:
                tf = doc_term_counts[q_term]
                num = tf * (k1 + 1.0)
                denom = tf + k1 * (1.0 - b + b * (d_len / max(avg_doc_len, 1.0)))
                score += idf[q_term] * (num / denom)
        scores.append(round(score, 6))

    return scores


class EvidenceRetriever:
    """Core evidence extraction and retrieval engine."""

    def __init__(self, config: Optional[RetrievalConfig] = None):
        self.config = config or RetrievalConfig()

    def retrieve(self, db: Session) -> EvidencePayload:
        """Execute retrieval workflow and return typed EvidencePayload.

        If non-dry-run, persists EvidenceSet and Evidence records to DB idempotently.
        """
        # 1. Candidate Pool Query with Eager Loading
        stmt = (
            select(Comment)
            .options(
                joinedload(Comment.video).joinedload(Video.program).joinedload(Program.channel),
                joinedload(Comment.predictions),
            )
            .where(Comment.processing_status == ProcessingStatusEnum.scored)
        )

        # Filter by video's program or channel if requested
        if self.config.program_id:
            stmt = stmt.join(Comment.video).where(Video.program_id == self.config.program_id)
        elif self.config.channel_id:
            stmt = stmt.join(Comment.video).join(Video.program).where(Program.channel_id == self.config.channel_id)

        # Date window filtering
        if self.config.start_date:
            stmt = stmt.where(Comment.posted_at >= self.config.start_date)
        if self.config.end_date:
            stmt = stmt.where(Comment.posted_at <= self.config.end_date)

        raw_comments = list(db.execute(stmt).scalars().unique())

        # 2. Quality & Classification Filtering
        candidates: List[Tuple[Comment, str, str, float, float]] = []

        for c in raw_comments:
            # Text substance check
            clean_text = c.text_clean or ""
            words = clean_text.split()
            if len(clean_text) < self.config.min_clean_text_length or len(words) < self.config.min_word_count:
                continue

            # Map predictions
            preds = {}
            for p in c.predictions:
                l_key = p.layer.value if hasattr(p.layer, "value") else str(p.layer)
                preds[l_key] = p
                preds[p.layer] = p

            l1_pred = preds.get(LayerEnum.layer1) or preds.get("layer1")
            if not l1_pred or l1_pred.label == "NOISE" or l1_pred.confidence < self.config.min_layer1_confidence:
                continue

            l2_pred = preds.get(LayerEnum.layer2) or preds.get("layer2")
            l4_pred = preds.get(LayerEnum.layer4) or preds.get("layer4")

            l2_topic = l2_pred.label if l2_pred else None
            l2_conf = l2_pred.confidence if l2_pred else 0.0

            l4_stance = l4_pred.label if l4_pred else None
            l4_conf = l4_pred.confidence if l4_pred else 0.0

            # Topic filter check
            if self.config.topic and l2_topic != self.config.topic:
                continue
            if l2_pred and l2_conf < self.config.min_layer2_confidence:
                continue

            # Stance filter check (if specific stance requested)
            if self.config.stance != "ALL" and l4_stance != self.config.stance:
                continue
            if l4_pred and l4_conf < self.config.min_layer4_confidence:
                continue

            candidates.append((c, l2_topic or "UNKNOWN", l4_stance or "UNKNOWN", l2_conf, l4_conf))

        total_matching_count = len(candidates)
        if not candidates:
            return self._build_empty_payload(total_matching_count=0)

        # 3. BM25 Relevance Scoring
        texts_to_score = [c[0].text_clean for c in candidates]
        bm25_scores = _compute_bm25_scores(texts_to_score, self.config.keywords)

        # 4. Attach scores & Perform Exact / Near-Duplicate Control
        scored_candidates = []
        seen_texts: Dict[str, Tuple[Comment, float]] = {}

        for (comment, topic, stance, l2_conf, l4_conf), score in zip(candidates, bm25_scores):
            norm_text = (comment.text_clean or "").strip().lower()

            # Exact text deduplication: keep highest relevance score / like_count
            if norm_text in seen_texts:
                prev_c, prev_score = seen_texts[norm_text]
                if score > prev_score or (score == prev_score and comment.like_count > prev_c.like_count):
                    seen_texts[norm_text] = (comment, score)
                continue
            else:
                seen_texts[norm_text] = (comment, score)

            scored_candidates.append({
                "comment": comment,
                "topic": topic,
                "stance": stance,
                "l2_conf": l2_conf,
                "l4_conf": l4_conf,
                "relevance_score": score,
                "tokens": _tokenize(norm_text),
            })

        # Near-duplicate filtering via Jaccard similarity
        unique_candidates = []
        for cand in scored_candidates:
            is_near_dup = False
            for accepted in unique_candidates:
                sim = _jaccard_similarity(cand["tokens"], accepted["tokens"])
                if sim >= self.config.near_duplicate_threshold:
                    is_near_dup = True
                    break
            if not is_near_dup:
                unique_candidates.append(cand)

        # 5. Multi-Stance Proportional Allocation (when stance='ALL') vs Single Stance
        final_selected = []
        if self.config.stance == "ALL" and self.config.top_k > 0:
            # Group by stance
            stance_groups: Dict[str, List[dict]] = {"STANCE_CRIT": [], "STANCE_NEUT": [], "STANCE_SUPP": []}
            for cand in unique_candidates:
                st = cand["stance"]
                if st in stance_groups:
                    stance_groups[st].append(cand)
                else:
                    stance_groups.setdefault(st, []).append(cand)

            # Deterministic sorting within each stance group
            for st in stance_groups:
                stance_groups[st].sort(
                    key=lambda x: (
                        round(x["relevance_score"], 6),
                        x["comment"].posted_at or datetime.min,
                        x["comment"].like_count,
                        str(x["comment"].id),
                    ),
                    reverse=True,
                )
                # Reverse for UUID ascending
                # Re-sort accurately with explicit tuple:
                stance_groups[st] = sorted(
                    stance_groups[st],
                    key=lambda x: (
                        -round(x["relevance_score"], 6),
                        -(x["comment"].posted_at.timestamp() if x["comment"].posted_at else 0),
                        -x["comment"].like_count,
                        str(x["comment"].id),
                    ),
                )

            # Calculate proportional quotas
            total_cand = len(unique_candidates)
            quotas = {}
            for st, items in stance_groups.items():
                if total_cand > 0:
                    quotas[st] = max(1 if items else 0, round(self.config.top_k * (len(items) / total_cand)))
                else:
                    quotas[st] = 0

            # Collect candidates respecting quotas & video diversity caps
            video_counts: Dict[str, int] = {}
            for st, items in stance_groups.items():
                q = quotas.get(st, 0)
                st_selected = 0
                for cand in items:
                    if st_selected >= q or len(final_selected) >= self.config.top_k:
                        break
                    v_id = str(cand["comment"].video_id)
                    if video_counts.get(v_id, 0) >= self.config.max_per_video:
                        continue
                    video_counts[v_id] = video_counts.get(v_id, 0) + 1
                    final_selected.append(cand)
                    st_selected += 1

            # Fill remaining top_k slots if quotas didn't fill top_k
            if len(final_selected) < self.config.top_k:
                sorted_all = sorted(
                    unique_candidates,
                    key=lambda x: (
                        -round(x["relevance_score"], 6),
                        -(x["comment"].posted_at.timestamp() if x["comment"].posted_at else 0),
                        -x["comment"].like_count,
                        str(x["comment"].id),
                    ),
                )
                for cand in sorted_all:
                    if len(final_selected) >= self.config.top_k:
                        break
                    if cand in final_selected:
                        continue
                    v_id = str(cand["comment"].video_id)
                    if video_counts.get(v_id, 0) >= self.config.max_per_video:
                        continue
                    video_counts[v_id] = video_counts.get(v_id, 0) + 1
                    final_selected.append(cand)

        else:
            # Targeted stance or overall top-K
            sorted_all = sorted(
                unique_candidates,
                key=lambda x: (
                    -round(x["relevance_score"], 6),
                    -(x["comment"].posted_at.timestamp() if x["comment"].posted_at else 0),
                    -x["comment"].like_count,
                    str(x["comment"].id),
                ),
            )

            video_counts: Dict[str, int] = {}
            for cand in sorted_all:
                if len(final_selected) >= self.config.top_k:
                    break
                v_id = str(cand["comment"].video_id)
                if video_counts.get(v_id, 0) >= self.config.max_per_video:
                    continue
                video_counts[v_id] = video_counts.get(v_id, 0) + 1
                final_selected.append(cand)

        # 6. Final Deterministic Order across the evidence set
        final_selected = sorted(
            final_selected,
            key=lambda x: (
                -round(x["relevance_score"], 6),
                -(x["comment"].posted_at.timestamp() if x["comment"].posted_at else 0),
                -x["comment"].like_count,
                str(x["comment"].id),
            ),
        )

        # 7. Persist EvidenceSet and Evidence records in DB idempotently
        evidence_items_for_db = []
        for rank, cand in enumerate(final_selected, start=1):
            comment = cand["comment"]
            evidence_items_for_db.append({
                "comment_id": comment.id,
                "evidence_type": "retrieved_sample",
                "layer": LayerEnum.layer2 if cand["topic"] != "UNKNOWN" else None,
                "label": cand["topic"],
                "confidence": cand["l2_conf"],
                "relevance_score": cand["relevance_score"],
                "rank": rank,
            })

        evidence_set_record = insert_evidence_set(
            db,
            query_params=self.config.to_dict(),
            items=evidence_items_for_db,
            retrieval_method=self.config.retrieval_method,
        )
        db.commit()

        # 8. Build Typed EvidencePayload
        payload_items = []
        for rank, cand in enumerate(final_selected, start=1):
            c = cand["comment"]
            v = c.video
            p = v.program if v else None
            ch = p.channel if p else None

            # Find matching Evidence DB ID
            ev_id = str(evidence_set_record.id)
            for ev in evidence_set_record.evidence_items:
                if ev.comment_id == c.id:
                    ev_id = str(ev.id)
                    break

            payload_items.append(
                EvidenceItem(
                    rank=rank,
                    evidence_id=ev_id,
                    comment_id=str(c.id),
                    text_raw=c.text_raw,
                    text_clean=c.text_clean,
                    posted_at=c.posted_at.isoformat() if c.posted_at else None,
                    video_id=str(v.id) if v else "",
                    video_title=v.title if v else None,
                    program_name=p.name if p else "",
                    channel_name=ch.name if ch else "",
                    layer2_topic=cand["topic"],
                    layer2_confidence=cand["l2_conf"],
                    layer4_stance=cand["stance"],
                    layer4_confidence=cand["l4_conf"],
                    like_count=c.like_count,
                    relevance_score=cand["relevance_score"],
                )
            )

        return EvidencePayload(
            evidence_set_id=str(evidence_set_record.id),
            retrieved_at=evidence_set_record.retrieved_at.isoformat(),
            retrieval_metadata=self.config.to_dict(),
            evidence_count=len(payload_items),
            total_matching_count=total_matching_count,
            retrieval_method=self.config.retrieval_method,
            evidence_items=payload_items,
        )

    def _build_empty_payload(self, total_matching_count: int = 0) -> EvidencePayload:
        import uuid
        return EvidencePayload(
            evidence_set_id=str(uuid.uuid4()),
            retrieved_at=datetime.utcnow().isoformat(),
            retrieval_metadata=self.config.to_dict(),
            evidence_count=0,
            total_matching_count=total_matching_count,
            retrieval_method=self.config.retrieval_method,
            evidence_items=[],
        )
