"""Repository functions for Public Pulse — the only place ORM queries live.

All public functions:
  - Accept a SQLAlchemy Session as their first argument.
  - Are idempotent / safe to call repeatedly (scraper re-runs won't duplicate).
  - Use a merge pattern (SELECT → INSERT/UPDATE) that works for both
    PostgreSQL (production) and SQLite (tests) without dialect-specific
    ON CONFLICT syntax.
  - Call session.flush() so callers can inspect PKs before commit; callers
    are responsible for session.commit() / session.rollback().

Active inference architecture: Layer 1 → Layer 2 + Layer 4.
Layer 3 does not exist and must not appear in any query or comment here.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import List, Optional

import uuid as uuid_mod

from sqlalchemy import String, select, func, desc, cast
from sqlalchemy.orm import Session, selectinload

from public_pulse.database.models import (
    Annotation,
    Channel,
    Comment,
    Evidence,
    EvidenceSet,
    Insight,
    JobRecord,
    LayerEnum,
    LayerPrediction,
    ModelVersion,
    PipelineRun,
    PipelineRunStatusEnum,
    ProcessingStatusEnum,
    Program,
    VerificationResult,
    Video,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# channels
# ---------------------------------------------------------------------------


def upsert_channel(
    db: Session,
    *,
    youtube_channel_id: str,
    name: str,
    channel_url: Optional[str] = None,
    description: Optional[str] = None,
    subscriber_count: Optional[int] = None,
) -> Channel:
    """Insert a new channel or update an existing one by youtube_channel_id.

    Returns the Channel ORM object (flushed but not committed).
    """
    stmt = select(Channel).where(Channel.youtube_channel_id == youtube_channel_id)
    channel = db.execute(stmt).scalar_one_or_none()

    if channel is None:
        channel = Channel(
            youtube_channel_id=youtube_channel_id,
            name=name,
            channel_url=channel_url,
            description=description,
            subscriber_count=subscriber_count,
        )
        db.add(channel)
        log.debug("Inserted channel %r", youtube_channel_id)
    else:
        channel.name = name
        if channel_url is not None:
            channel.channel_url = channel_url
        if description is not None:
            channel.description = description
        if subscriber_count is not None:
            channel.subscriber_count = subscriber_count
        log.debug("Updated channel %r", youtube_channel_id)

    db.flush()
    return channel


# ---------------------------------------------------------------------------
# programs
# ---------------------------------------------------------------------------


def upsert_program(
    db: Session,
    *,
    channel_id,
    name: str,
    platform: str = "youtube",
    program_type: Optional[str] = None,
    is_active: bool = True,
) -> Program:
    """Insert a new program or update an existing one by (channel_id, name).

    program_type is intentionally nullable — do NOT pass invented values.
    Returns the Program ORM object (flushed but not committed).
    """
    stmt = select(Program).where(
        Program.channel_id == channel_id,
        Program.name == name,
    )
    program = db.execute(stmt).scalar_one_or_none()

    if program is None:
        program = Program(
            channel_id=channel_id,
            name=name,
            platform=platform,
            program_type=program_type,
            is_active=is_active,
        )
        db.add(program)
        log.debug("Inserted program %r", name)
    else:
        program.platform = platform
        program.is_active = is_active
        if program_type is not None:
            program.program_type = program_type
        log.debug("Updated program %r", name)

    db.flush()
    return program


# ---------------------------------------------------------------------------
# videos
# ---------------------------------------------------------------------------


def upsert_video(
    db: Session,
    *,
    program_id,
    youtube_video_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    published_at: Optional[datetime] = None,
    duration_seconds: Optional[int] = None,
    is_live: bool = False,
    comment_count: Optional[int] = None,
) -> Video:
    """Insert a new video or update an existing one by youtube_video_id.

    Returns the Video ORM object (flushed but not committed).
    """
    stmt = select(Video).where(Video.youtube_video_id == youtube_video_id)
    video = db.execute(stmt).scalar_one_or_none()

    if video is None:
        video = Video(
            program_id=program_id,
            youtube_video_id=youtube_video_id,
            title=title,
            description=description,
            published_at=published_at,
            duration_seconds=duration_seconds,
            is_live=is_live,
            comment_count=comment_count,
        )
        db.add(video)
        log.debug("Inserted video %r", youtube_video_id)
    else:
        if title is not None:
            video.title = title
        if description is not None:
            video.description = description
        if published_at is not None:
            video.published_at = published_at
        if duration_seconds is not None:
            video.duration_seconds = duration_seconds
        if comment_count is not None:
            video.comment_count = comment_count
        video.is_live = is_live
        log.debug("Updated video %r", youtube_video_id)

    db.flush()
    return video


# ---------------------------------------------------------------------------
# comments
# ---------------------------------------------------------------------------


def upsert_comment(
    db: Session,
    *,
    video_id,
    youtube_comment_id: str,
    text_raw: str,
    text_clean: str,
    author_hash: Optional[str] = None,
    like_count: int = 0,
    reply_count: int = 0,
    posted_at: Optional[datetime] = None,
    is_reply: bool = False,
    parent_comment_id=None,
) -> Comment:
    """Insert a new comment or return the existing one by youtube_comment_id.

    text_raw and text_clean are stored as separate columns:
        text_raw   → Layer 1 input (no preprocessing)
        text_clean → Layer 2 / Layer 4 input (output of clean_text())

    If the comment already exists, its text fields and counts are updated.
    Returns the Comment ORM object (flushed but not committed).
    """
    stmt = select(Comment).where(Comment.youtube_comment_id == youtube_comment_id)
    comment = db.execute(stmt).scalar_one_or_none()

    if comment is None:
        comment = Comment(
            video_id=video_id,
            youtube_comment_id=youtube_comment_id,
            text_raw=text_raw,
            text_clean=text_clean,
            author_hash=author_hash,
            like_count=like_count,
            reply_count=reply_count,
            posted_at=posted_at,
            is_reply=is_reply,
            parent_comment_id=parent_comment_id,
            processing_status=ProcessingStatusEnum.pending,
        )
        db.add(comment)
        log.debug("Inserted comment %r", youtube_comment_id)
    else:
        # Update mutable fields on re-scrape
        comment.text_raw = text_raw
        comment.text_clean = text_clean
        comment.like_count = like_count
        comment.reply_count = reply_count
        if posted_at is not None:
            comment.posted_at = posted_at
        log.debug("Updated comment %r", youtube_comment_id)

    db.flush()
    return comment


# ---------------------------------------------------------------------------
# layer_predictions
# ---------------------------------------------------------------------------


def insert_predictions(
    db: Session,
    *,
    comment_id,
    model_version_id,
    predictions: List[dict],
) -> List[LayerPrediction]:
    """Insert layer predictions for a single comment.

    Each item in `predictions` must be a dict with keys:
        layer       str  — 'layer1', 'layer2', or 'layer4' (sub-issue layer invalid)
        label       str  — predicted label string
        label_id    int  — numeric class index
        confidence  float — softmax probability of predicted class

    Prediction rows are skipped if already present for this
    (comment_id, layer, model_version_id) combination.

    After insertion the comment's processing_status is updated:
        - If any Layer 1 prediction has label 'NOISE': noise_exit
        - Otherwise: scored

    Returns the list of inserted LayerPrediction objects.
    """
    inserted: List[LayerPrediction] = []
    now = datetime.now(timezone.utc)

    for pred_dict in predictions:
        layer_val = pred_dict["layer"]
        # Check for existing prediction (idempotency)
        existing = db.execute(
            select(LayerPrediction).where(
                LayerPrediction.comment_id == comment_id,
                LayerPrediction.layer == layer_val,
                LayerPrediction.model_version_id == model_version_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            log.debug(
                "Skipping duplicate prediction comment=%s layer=%s", comment_id, layer_val
            )
            continue

        pred = LayerPrediction(
            comment_id=comment_id,
            model_version_id=model_version_id,
            layer=layer_val,
            label=pred_dict["label"],
            label_id=pred_dict["label_id"],
            confidence=pred_dict["confidence"],
            predicted_at=now,
        )
        db.add(pred)
        inserted.append(pred)

    db.flush()

    # Update comment processing_status based on Layer 1 result
    comment = db.get(Comment, comment_id)
    if comment is not None:
        layer1_preds = [p for p in predictions if p["layer"] == "layer1"]
        if layer1_preds and layer1_preds[0]["label"] == "NOISE":
            comment.processing_status = ProcessingStatusEnum.noise_exit
        elif inserted or _has_all_valid_predictions(db, comment_id, model_version_id):
            comment.processing_status = ProcessingStatusEnum.scored
        db.flush()

    return inserted


def _has_all_valid_predictions(
    db: Session, comment_id, model_version_id
) -> bool:
    """Return True if predictions for all three layers exist for this comment."""
    layers_present = {
        row[0]
        for row in db.execute(
            select(LayerPrediction.layer).where(
                LayerPrediction.comment_id == comment_id,
                LayerPrediction.model_version_id == model_version_id,
            )
        )
    }
    return {LayerEnum.layer1, LayerEnum.layer2, LayerEnum.layer4} <= layers_present


# ---------------------------------------------------------------------------
# Queries used by the batch inference pipeline
# ---------------------------------------------------------------------------


def get_pending_comments(
    db: Session,
    *,
    limit: int = 500,
) -> List[Comment]:
    """Return up to `limit` comments with processing_status='pending'.

    Used by the batch inference pipeline (scripts/run_inference.py) to
    find unscored comments. Results are ordered by created_at ascending
    (oldest first) for reproducible batching.
    """
    stmt = (
        select(Comment)
        .where(Comment.processing_status == ProcessingStatusEnum.pending)
        .order_by(Comment.created_at.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())


def get_active_model_version(
    db: Session,
    layer: LayerEnum,
) -> Optional[ModelVersion]:
    """Return the currently active ModelVersion for the given layer, or None.

    layer must be LayerEnum.layer1, LayerEnum.layer2, or LayerEnum.layer4.
    Returns None if no active version is registered for that layer.
    """
    stmt = select(ModelVersion).where(
        ModelVersion.layer == layer,
        ModelVersion.is_active.is_(True),
    )
    return db.execute(stmt).scalar_one_or_none()


def set_active_model_version(
    db: Session,
    *,
    model_version_id,
) -> ModelVersion:
    """Mark a ModelVersion as active and deactivate any previous active version
    for the same layer.

    This enforces the at-most-one-active-per-layer rule at the application
    level. The PostgreSQL partial unique index (UNIQUE(layer) WHERE is_active)
    in the migration provides an additional DB-level guard.

    Returns the newly activated ModelVersion (flushed but not committed).
    """
    version = db.get(ModelVersion, model_version_id)
    if version is None:
        raise ValueError(f"ModelVersion {model_version_id!r} not found")

    # Deactivate any currently active version for the same layer
    stmt = select(ModelVersion).where(
        ModelVersion.layer == version.layer,
        ModelVersion.is_active.is_(True),
        ModelVersion.id != model_version_id,
    )
    for old in db.execute(stmt).scalars():
        old.is_active = False
        log.info(
            "Deactivated model version %s for layer %s", old.id, old.layer
        )

    version.is_active = True
    db.flush()
    log.info("Activated model version %s for layer %s", version.id, version.layer)
    return version


# ---------------------------------------------------------------------------
# evidence_sets
# ---------------------------------------------------------------------------


def insert_evidence_set(
    db: Session,
    *,
    query_params: dict,
    items: list[dict],
    retrieval_method: str = "hybrid_bm25_v1",
) -> EvidenceSet:
    """Create an EvidenceSet record and its associated Evidence items idempotently.

    items is a list of dicts:
      [
        {
          "comment_id": UUID,
          "evidence_type": str (default 'retrieved_sample'),
          "layer": LayerEnum or None,
          "label": str or None,
          "confidence": float or None,
          "relevance_score": float or None,
          "rank": int or None,
        },
        ...
      ]

    Flushes changes to DB so calling code can read assigned IDs. Caller commits.
    """
    ev_set = EvidenceSet(
        query_params=query_params,
        retrieval_method=retrieval_method,
    )
    db.add(ev_set)
    db.flush()

    for item in items:
        comment_id = getattr(item, "comment_id", None) if not isinstance(item, dict) else item.get("comment_id")
        if isinstance(comment_id, str):
            try:
                comment_id = uuid_mod.UUID(comment_id)
            except ValueError:
                pass

        evidence_type = getattr(item, "evidence_type", "retrieved_sample") if not isinstance(item, dict) else item.get("evidence_type", "retrieved_sample")
        layer = getattr(item, "layer", None) if not isinstance(item, dict) else item.get("layer")
        label = getattr(item, "label", None) if not isinstance(item, dict) else item.get("label")
        confidence = getattr(item, "confidence", None) if not isinstance(item, dict) else item.get("confidence")
        relevance_score = getattr(item, "relevance_score", None) if not isinstance(item, dict) else item.get("relevance_score")
        rank = getattr(item, "rank", None) if not isinstance(item, dict) else item.get("rank")

        # Check idempotency per (evidence_set_id, comment_id)
        stmt = select(Evidence).where(
            Evidence.evidence_set_id == ev_set.id,
            Evidence.comment_id == comment_id,
        )
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            continue

        ev = Evidence(
            evidence_set_id=ev_set.id,
            comment_id=comment_id,
            evidence_type=evidence_type,
            layer=layer,
            label=label,
            confidence=confidence,
            relevance_score=relevance_score,
            rank=rank,
        )
        db.add(ev)

    db.flush()
    return ev_set


def get_evidence_set(
    db: Session,
    evidence_set_id,
) -> Optional[EvidenceSet]:
    """Fetch an EvidenceSet by ID, including its associated evidence_items.

    Accepts either a uuid.UUID object or a UUID string.
    Uses a select() query instead of db.get() to ensure correct behaviour
    in both PostgreSQL (production) and SQLite (tests), where UUID is stored
    as a string and identity-map lookups may fail after session.commit().
    """
    if isinstance(evidence_set_id, str):
        try:
            evidence_set_id = uuid_mod.UUID(evidence_set_id)
        except ValueError:
            return None
    id_str = str(evidence_set_id)
    # Primary lookup: match by UUID object (PostgreSQL)
    stmt = (
        select(EvidenceSet)
        .where(EvidenceSet.id == evidence_set_id)
        .options(selectinload(EvidenceSet.evidence_items))
    )
    result = db.execute(stmt).scalar_one_or_none()
    if result is None:
        # Fallback: match by string cast (SQLite stores UUIDs as text)
        stmt_str = (
            select(EvidenceSet)
            .where(EvidenceSet.id.cast(String) == id_str)
            .options(selectinload(EvidenceSet.evidence_items))
        )
        result = db.execute(stmt_str).scalar_one_or_none()
    return result


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------


def insert_insight(
    db: Session,
    *,
    evidence_set_id: Optional[Any] = None,
    program_id: Optional[Any] = None,
    insight_type: str = "grounded_llm_v1",
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    payload_json: dict,
    generation_status: str = "success",
    error_message: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    prompt_version: Optional[str] = None,
    generation_params_json: Optional[dict] = None,
) -> Insight:
    """Insert or retrieve an existing Insight idempotently by (evidence_set_id, insight_type).

    If an Insight already exists for this (evidence_set_id, insight_type), returns
    the existing record. Otherwise, creates and flushes a new Insight record.
    Caller is responsible for session.commit().
    """
    if evidence_set_id is not None:
        if isinstance(evidence_set_id, str):
            try:
                evidence_set_id = uuid_mod.UUID(evidence_set_id)
            except ValueError:
                pass
        id_str = str(evidence_set_id)
        stmt = select(Insight).where(
            Insight.evidence_set_id == evidence_set_id,
            Insight.insight_type == insight_type,
        )
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is None and isinstance(evidence_set_id, uuid_mod.UUID):
            # Fallback for SQLite string conversion
            stmt_str = select(Insight).where(
                Insight.evidence_set_id.cast(String) == id_str,
                Insight.insight_type == insight_type,
            )
            existing = db.execute(stmt_str).scalar_one_or_none()

        if existing is not None:
            log.info(
                "Insight already exists for evidence_set_id %s, insight_type %s",
                id_str,
                insight_type,
            )
            return existing

    if program_id is not None and isinstance(program_id, str):
        try:
            program_id = uuid_mod.UUID(program_id)
        except ValueError:
            pass

    insight = Insight(
        evidence_set_id=evidence_set_id,
        program_id=program_id,
        insight_type=insight_type,
        period_start=period_start,
        period_end=period_end,
        payload_json=payload_json,
        generation_status=generation_status,
        error_message=error_message,
        llm_provider=llm_provider,
        llm_model=llm_model,
        prompt_version=prompt_version,
        generation_params_json=generation_params_json,
    )
    db.add(insight)
    db.flush()
    return insight


def get_insight(
    db: Session,
    insight_id,
) -> Optional[Insight]:
    """Fetch an Insight by ID."""
    if isinstance(insight_id, str):
        try:
            insight_id = uuid_mod.UUID(insight_id)
        except ValueError:
            return None
    id_str = str(insight_id)
    stmt = select(Insight).where(Insight.id == insight_id)
    result = db.execute(stmt).scalar_one_or_none()
    if result is None:
        stmt_str = select(Insight).where(Insight.id.cast(String) == id_str)
        result = db.execute(stmt_str).scalar_one_or_none()
    return result


def list_insights(
    db: Session,
    *,
    program_id: Optional[Any] = None,
    generation_status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Insight]:
    """Fetch insights with optional program_id and generation_status filters."""
    stmt = select(Insight)
    if program_id is not None:
        if isinstance(program_id, str):
            try:
                program_id = uuid_mod.UUID(program_id)
            except ValueError:
                pass
        stmt = stmt.where(Insight.program_id == program_id)

    if generation_status:
        if generation_status in ("completed", "success"):
            stmt = stmt.where(Insight.generation_status.in_(["completed", "success"]))
        else:
            stmt = stmt.where(Insight.generation_status == generation_status)

    stmt = stmt.order_by(desc(Insight.generated_at).nullslast(), desc(Insight.id)).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())



# ---------------------------------------------------------------------------
# verification_results
# ---------------------------------------------------------------------------


def insert_verification_result(
    db: Session,
    *,
    insight_id,
    evidence_set_id,
    verifier_method: str = "hybrid_nli_v1",
    verifier_model: Optional[str] = None,
    grounding_score: float = 0.0,
    claim_support_rate: float = 0.0,
    unsupported_claim_rate: float = 0.0,
    contradiction_rate: float = 0.0,
    verification_details_json: dict,
) -> VerificationResult:
    """Insert or update a VerificationResult idempotently by (insight_id, verifier_method)."""
    if isinstance(insight_id, str):
        try:
            insight_id = uuid_mod.UUID(insight_id)
        except ValueError:
            pass
    if isinstance(evidence_set_id, str):
        try:
            evidence_set_id = uuid_mod.UUID(evidence_set_id)
        except ValueError:
            pass

    ins_id_str = str(insight_id)
    stmt = select(VerificationResult).where(
        VerificationResult.insight_id == insight_id,
        VerificationResult.verifier_method == verifier_method,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing is None and isinstance(insight_id, uuid_mod.UUID):
        stmt_str = select(VerificationResult).where(
            VerificationResult.insight_id.cast(String) == ins_id_str,
            VerificationResult.verifier_method == verifier_method,
        )
        existing = db.execute(stmt_str).scalar_one_or_none()

    if existing is not None:
        log.info("VerificationResult already exists for insight_id %s, method %s", ins_id_str, verifier_method)
        return existing

    res = VerificationResult(
        insight_id=insight_id,
        evidence_set_id=evidence_set_id,
        verifier_method=verifier_method,
        verifier_model=verifier_model,
        grounding_score=grounding_score,
        claim_support_rate=claim_support_rate,
        unsupported_claim_rate=unsupported_claim_rate,
        contradiction_rate=contradiction_rate,
        verification_details_json=verification_details_json,
    )
    db.add(res)
    db.flush()
    return res


def get_verification_result(
    db: Session,
    target_id,
) -> Optional[VerificationResult]:
    """Fetch a VerificationResult by VerificationResult.id or Insight.id."""
    if isinstance(target_id, str):
        try:
            target_id = uuid_mod.UUID(target_id)
        except ValueError:
            return None
    stmt = select(VerificationResult).where(
        (VerificationResult.id == target_id) | (VerificationResult.insight_id == target_id)
    )
    result = db.execute(stmt).scalar_one_or_none()
    if result is None:
        id_str = str(target_id)
        stmt_str = select(VerificationResult).where(
            (VerificationResult.id.cast(String) == id_str)
            | (VerificationResult.insight_id.cast(String) == id_str)
        )
        result = db.execute(stmt_str).scalar_one_or_none()
    return result





# ---------------------------------------------------------------------------
# Phase 11: Catalog & Analytics Repository Functions
# ---------------------------------------------------------------------------


def list_channels(db: Session) -> List[Channel]:
    """Fetch all channels."""
    stmt = select(Channel).order_by(Channel.name)
    return list(db.execute(stmt).scalars().all())


def get_channel(db: Session, channel_id) -> Optional[Channel]:
    """Fetch channel by ID or YouTube channel ID."""
    if isinstance(channel_id, str):
        try:
            uid = uuid_mod.UUID(channel_id)
            stmt = select(Channel).where(Channel.id == uid)
            res = db.execute(stmt).scalar_one_or_none()
            if res:
                return res
        except ValueError:
            pass
        stmt = select(Channel).where(Channel.youtube_channel_id == channel_id)
        return db.execute(stmt).scalar_one_or_none()
    stmt = select(Channel).where(Channel.id == channel_id)
    return db.execute(stmt).scalar_one_or_none()


def list_programs(
    db: Session,
    *,
    channel_id: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[Program]:
    """Fetch programs, optionally filtered by channel or active status."""
    stmt = select(Program).options(selectinload(Program.channel))
    if channel_id:
        try:
            c_uid = uuid_mod.UUID(channel_id)
            stmt = stmt.where(Program.channel_id == c_uid)
        except ValueError:
            stmt = stmt.join(Channel).where(Channel.youtube_channel_id == channel_id)
    if is_active is not None:
        stmt = stmt.where(Program.is_active == is_active)
    stmt = stmt.order_by(Program.name)
    return list(db.execute(stmt).scalars().all())


def get_program(db: Session, program_id) -> Optional[Program]:
    """Fetch program by ID with channel loaded."""
    if isinstance(program_id, str):
        try:
            p_uid = uuid_mod.UUID(program_id)
        except ValueError:
            return None
        program_id = p_uid
    stmt = select(Program).options(selectinload(Program.channel)).where(Program.id == program_id)
    return db.execute(stmt).scalar_one_or_none()


def list_videos_for_program(
    db: Session,
    program_id,
    *,
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Video]:
    """Fetch videos for a program with pagination and date filter."""
    if isinstance(program_id, str):
        try:
            program_id = uuid_mod.UUID(program_id)
        except ValueError:
            return []
    stmt = select(Video).where(Video.program_id == program_id)
    if start_date:
        stmt = stmt.where(Video.published_at >= start_date)
    if end_date:
        stmt = stmt.where(Video.published_at <= end_date)
    stmt = stmt.order_by(desc(Video.published_at)).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def get_video(db: Session, video_id) -> Optional[Video]:
    """Fetch video by ID or YouTube video ID."""
    if isinstance(video_id, str):
        try:
            uid = uuid_mod.UUID(video_id)
            stmt = select(Video).where(Video.id == uid)
            res = db.execute(stmt).scalar_one_or_none()
            if res:
                return res
        except ValueError:
            pass
        stmt = select(Video).where(Video.youtube_video_id == video_id)
        return db.execute(stmt).scalar_one_or_none()
    stmt = select(Video).where(Video.id == video_id)
    return db.execute(stmt).scalar_one_or_none()


def list_insights(
    db: Session,
    *,
    program_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    generation_status: Optional[str] = None,
) -> List[Insight]:
    """Fetch insights with optional program and status filters."""
    stmt = select(Insight)
    if program_id:
        try:
            p_uid = uuid_mod.UUID(program_id)
            stmt = stmt.where(Insight.program_id == p_uid)
        except ValueError:
            return []
    if generation_status:
        stmt = stmt.where(Insight.generation_status == generation_status)
    stmt = stmt.order_by(desc(Insight.generated_at)).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# Job Management Functions
# ---------------------------------------------------------------------------


def create_job(db: Session, job_type: str, reference_id: Optional[str] = None) -> JobRecord:
    """Create a new pending background job record."""
    job = JobRecord(job_type=job_type, status="pending", reference_id=reference_id)
    db.add(job)
    db.flush()
    return job


def get_job(db: Session, job_id) -> Optional[JobRecord]:
    """Fetch a job record by ID."""
    if isinstance(job_id, str):
        try:
            job_id = uuid_mod.UUID(job_id)
        except ValueError:
            return None
    stmt = select(JobRecord).where(JobRecord.id == job_id)
    return db.execute(stmt).scalar_one_or_none()


def update_job_status(
    db: Session,
    job_id,
    status: str,
    reference_id: Optional[str] = None,
    error: Optional[str] = None,
) -> Optional[JobRecord]:
    """Update job status and optional completion data."""
    job = get_job(db, job_id)
    if not job:
        return None
    job.status = status
    if reference_id:
        job.reference_id = reference_id
    if error:
        job.error = error
    if status in ("completed", "error"):
        job.completed_at = datetime.now(timezone.utc)
    db.flush()
    return job


# ---------------------------------------------------------------------------
# Maximum-Analysis Analytical Aggregations
# ---------------------------------------------------------------------------


def _apply_comment_filters(
    stmt,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    video_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Helper to join Video / Program / Channel and apply scope/date filters on Comment queries."""
    if video_id:
        try:
            v_uid = uuid_mod.UUID(video_id)
            stmt = stmt.where(Comment.video_id == v_uid)
        except ValueError:
            pass
    elif program_id or channel_id:
        stmt = stmt.join(Video, Comment.video_id == Video.id)

    if program_id:
        try:
            p_uid = uuid_mod.UUID(program_id)
            stmt = stmt.where(Video.program_id == p_uid)
        except ValueError:
            pass
    elif channel_id:
        stmt = stmt.join(Program, Video.program_id == Program.id)
        try:
            c_uid = uuid_mod.UUID(channel_id)
            stmt = stmt.where(Program.channel_id == c_uid)
        except ValueError:
            pass

    if start_date:
        stmt = stmt.where(Comment.posted_at >= start_date)
    if end_date:
        stmt = stmt.where(Comment.posted_at <= end_date)

    return stmt


def get_analytics_overview(
    db: Session,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    video_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Calculate overview KPIs (total comments, valid, noise, noise rate, etc.)."""
    from sqlalchemy import case as sa_case  # local import to avoid top-level change

    stmt = select(
        func.count(Comment.id).label("total_comments"),
        func.sum(sa_case((Comment.processing_status == ProcessingStatusEnum.scored, 1), else_=0)).label("scored_comments"),
        func.sum(sa_case((Comment.processing_status == ProcessingStatusEnum.noise_exit, 1), else_=0)).label("noise_comments"),
        func.sum(sa_case((Comment.processing_status == ProcessingStatusEnum.pending, 1), else_=0)).label("pending_comments"),
    )
    stmt = _apply_comment_filters(
        stmt,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        start_date=start_date,
        end_date=end_date,
    )
    res = db.execute(stmt).one()
    total = int(res.total_comments or 0)
    scored = int(res.scored_comments or 0)
    noise = int(res.noise_comments or 0)
    pending = int(res.pending_comments or 0)
    valid = scored

    noise_rate = round(noise / total, 4) if total > 0 else 0.0

    v_stmt = select(func.count(Video.id))
    if program_id:
        try:
            v_stmt = v_stmt.where(Video.program_id == uuid_mod.UUID(program_id))
        except ValueError:
            pass
    elif channel_id:
        try:
            v_stmt = v_stmt.join(Program).where(Program.channel_id == uuid_mod.UUID(channel_id))
        except ValueError:
            pass
    total_videos = db.execute(v_stmt).scalar() or 0

    p_stmt = select(func.count(Program.id))
    if channel_id:
        try:
            p_stmt = p_stmt.where(Program.channel_id == uuid_mod.UUID(channel_id))
        except ValueError:
            pass
    total_programs = db.execute(p_stmt).scalar() or 0

    total_channels = db.execute(select(func.count(Channel.id))).scalar() or 0

    return {
        "total_comments": total,
        "valid_comments": valid,
        "noise_comments": noise,
        "pending_comments": pending,
        "noise_rate": noise_rate,
        "total_videos": total_videos,
        "total_programs": total_programs,
        "total_channels": total_channels,
        "avg_comments_per_video": round(total / total_videos, 2) if total_videos > 0 else 0.0,
    }


def get_topic_distribution(
    db: Session,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    video_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[dict]:
    """Calculate Layer 2 macro-topic breakdown for VALID comments."""
    stmt = (
        select(LayerPrediction.label, func.count(LayerPrediction.id).label("cnt"))
        .join(Comment, LayerPrediction.comment_id == Comment.id)
        .where(LayerPrediction.layer == LayerEnum.layer2)
    )
    stmt = _apply_comment_filters(
        stmt,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        start_date=start_date,
        end_date=end_date,
    )
    stmt = stmt.group_by(LayerPrediction.label).order_by(desc("cnt"))
    rows = db.execute(stmt).all()

    total = sum(r.cnt for r in rows)
    return [
        {
            "topic": r.label,
            "count": r.cnt,
            "percentage": round(r.cnt / total * 100, 2) if total > 0 else 0.0,
        }
        for r in rows
    ]


def get_stance_distribution(
    db: Session,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    video_id: Optional[str] = None,
    topic_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[dict]:
    """Calculate Layer 4 stance distribution (STANCE_CRIT, STANCE_NEUT, STANCE_SUPP)."""
    stmt = (
        select(LayerPrediction.label, func.count(LayerPrediction.id).label("cnt"))
        .join(Comment, LayerPrediction.comment_id == Comment.id)
        .where(LayerPrediction.layer == LayerEnum.layer4)
    )

    if topic_filter:
        l2_alias = select(LayerPrediction.comment_id).where(
            LayerPrediction.layer == LayerEnum.layer2,
            LayerPrediction.label == topic_filter,
        )
        stmt = stmt.where(Comment.id.in_(l2_alias))

    stmt = _apply_comment_filters(
        stmt,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        start_date=start_date,
        end_date=end_date,
    )
    stmt = stmt.group_by(LayerPrediction.label).order_by(desc("cnt"))
    rows = db.execute(stmt).all()

    total = sum(r.cnt for r in rows)
    return [
        {
            "stance": r.label,
            "count": r.cnt,
            "percentage": round(r.cnt / total * 100, 2) if total > 0 else 0.0,
        }
        for r in rows
    ]


def get_topic_stance_matrix(
    db: Session,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    video_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Calculate Topic x Stance cross-tabulation matrix."""
    lp2 = select(LayerPrediction.comment_id, LayerPrediction.label.label("topic")).where(
        LayerPrediction.layer == LayerEnum.layer2
    ).subquery("lp2")
    lp4 = select(LayerPrediction.comment_id, LayerPrediction.label.label("stance")).where(
        LayerPrediction.layer == LayerEnum.layer4
    ).subquery("lp4")

    stmt = (
        select(lp2.c.topic, lp4.c.stance, func.count(Comment.id).label("cnt"))
        .join(lp2, Comment.id == lp2.c.comment_id)
        .join(lp4, Comment.id == lp4.c.comment_id)
    )
    stmt = _apply_comment_filters(
        stmt,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        start_date=start_date,
        end_date=end_date,
    )
    stmt = stmt.group_by(lp2.c.topic, lp4.c.stance)
    rows = db.execute(stmt).all()

    matrix = {}
    for r in rows:
        if r.topic not in matrix:
            matrix[r.topic] = {}
        matrix[r.topic][r.stance] = r.cnt

    return matrix


def get_entity_topic_matrix(
    db: Session,
    *,
    entity_type: str = "program",
    channel_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Calculate Program x Topic or Channel x Topic breakdown."""
    if entity_type == "channel":
        entity_name_col = Channel.name
        stmt = (
            select(entity_name_col, LayerPrediction.label.label("topic"), func.count(Comment.id).label("cnt"))
            .join(Video, Comment.video_id == Video.id)
            .join(Program, Video.program_id == Program.id)
            .join(Channel, Program.channel_id == Channel.id)
            .join(LayerPrediction, Comment.id == LayerPrediction.comment_id)
            .where(LayerPrediction.layer == LayerEnum.layer2)
        )
    else:
        entity_name_col = Program.name
        stmt = (
            select(entity_name_col, LayerPrediction.label.label("topic"), func.count(Comment.id).label("cnt"))
            .join(Video, Comment.video_id == Video.id)
            .join(Program, Video.program_id == Program.id)
            .join(LayerPrediction, Comment.id == LayerPrediction.comment_id)
            .where(LayerPrediction.layer == LayerEnum.layer2)
        )
        if channel_id:
            try:
                stmt = stmt.where(Program.channel_id == uuid_mod.UUID(channel_id))
            except ValueError:
                pass

    if start_date:
        stmt = stmt.where(Comment.posted_at >= start_date)
    if end_date:
        stmt = stmt.where(Comment.posted_at <= end_date)

    stmt = stmt.group_by(entity_name_col, LayerPrediction.label)
    rows = db.execute(stmt).all()

    matrix = {}
    for r in rows:
        if r[0] not in matrix:
            matrix[r[0]] = {}
        matrix[r[0]][r.topic] = r.cnt
    return matrix


def get_entity_stance_matrix(
    db: Session,
    *,
    entity_type: str = "program",
    channel_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Calculate Program x Stance or Channel x Stance breakdown."""
    if entity_type == "channel":
        entity_name_col = Channel.name
        stmt = (
            select(entity_name_col, LayerPrediction.label.label("stance"), func.count(Comment.id).label("cnt"))
            .join(Video, Comment.video_id == Video.id)
            .join(Program, Video.program_id == Program.id)
            .join(Channel, Program.channel_id == Channel.id)
            .join(LayerPrediction, Comment.id == LayerPrediction.comment_id)
            .where(LayerPrediction.layer == LayerEnum.layer4)
        )
    else:
        entity_name_col = Program.name
        stmt = (
            select(entity_name_col, LayerPrediction.label.label("stance"), func.count(Comment.id).label("cnt"))
            .join(Video, Comment.video_id == Video.id)
            .join(Program, Video.program_id == Program.id)
            .join(LayerPrediction, Comment.id == LayerPrediction.comment_id)
            .where(LayerPrediction.layer == LayerEnum.layer4)
        )
        if channel_id:
            try:
                stmt = stmt.where(Program.channel_id == uuid_mod.UUID(channel_id))
            except ValueError:
                pass

    if start_date:
        stmt = stmt.where(Comment.posted_at >= start_date)
    if end_date:
        stmt = stmt.where(Comment.posted_at <= end_date)

    stmt = stmt.group_by(entity_name_col, LayerPrediction.label)
    rows = db.execute(stmt).all()

    matrix = {}
    for r in rows:
        if r[0] not in matrix:
            matrix[r[0]] = {}
        matrix[r[0]][r.stance] = r.cnt
    return matrix


def get_volume_over_time(
    db: Session,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    video_id: Optional[str] = None,
    granularity: str = "daily",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[dict]:
    """Calculate volume trend time series."""
    date_col = func.date(Comment.posted_at)

    stmt = select(
        date_col.label("time_bucket"),
        func.count(Comment.id).label("total_comments"),
        func.count(
            func.nullif(Comment.processing_status != ProcessingStatusEnum.scored, True)
        ).label("valid_comments"),
        func.count(
            func.nullif(Comment.processing_status != ProcessingStatusEnum.noise_exit, True)
        ).label("noise_comments"),
    )
    stmt = _apply_comment_filters(
        stmt,
        program_id=program_id,
        channel_id=channel_id,
        video_id=video_id,
        start_date=start_date,
        end_date=end_date,
    )
    stmt = stmt.group_by("time_bucket").order_by("time_bucket")
    rows = db.execute(stmt).all()

    return [
        {
            "date": str(r.time_bucket or ""),
            "total_comments": r.total_comments or 0,
            "valid_comments": r.valid_comments or 0,
            "noise_comments": r.noise_comments or 0,
        }
        for r in rows
    ]


def get_period_over_period_comparison(
    db: Session,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    period_days: int = 30,
) -> dict:
    """Calculate period-over-period comparison metrics (current vs previous period)."""
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    cur_start = now - timedelta(days=period_days)
    prev_start = cur_start - timedelta(days=period_days)

    cur_overview = get_analytics_overview(
        db, program_id=program_id, channel_id=channel_id, start_date=cur_start, end_date=now
    )
    prev_overview = get_analytics_overview(
        db, program_id=program_id, channel_id=channel_id, start_date=prev_start, end_date=cur_start
    )

    cur_total = cur_overview["total_comments"]
    prev_total = prev_overview["total_comments"]

    vol_change_pct = (
        round((cur_total - prev_total) / prev_total * 100, 2)
        if prev_total > 0
        else 0.0
    )

    return {
        "period_days": period_days,
        "current_period": {
            "start_date": cur_start.isoformat(),
            "end_date": now.isoformat(),
            "metrics": cur_overview,
        },
        "previous_period": {
            "start_date": prev_start.isoformat(),
            "end_date": cur_start.isoformat(),
            "metrics": prev_overview,
        },
        "changes": {
            "volume_change_pct": vol_change_pct,
            "noise_rate_change": round(
                cur_overview["noise_rate"] - prev_overview["noise_rate"], 4
            ),
        },
    }


def get_video_episode_analytics(
    db: Session,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[dict]:
    """Fetch per-video analytical summaries (comment counts, stance distribution, top topic)."""
    stmt = select(Video).options(selectinload(Video.program))
    if program_id:
        try:
            stmt = stmt.where(Video.program_id == uuid_mod.UUID(program_id))
        except ValueError:
            pass
    elif channel_id:
        stmt = stmt.join(Program).where(Program.channel_id == uuid_mod.UUID(channel_id))

    stmt = stmt.order_by(desc(Video.published_at)).limit(limit).offset(offset)
    videos = db.execute(stmt).scalars().all()

    result = []
    for v in videos:
        v_id_str = str(v.id)
        overview = get_analytics_overview(db, video_id=v_id_str)
        topics = get_topic_distribution(db, video_id=v_id_str)
        stances = get_stance_distribution(db, video_id=v_id_str)

        result.append(
            {
                "video_id": v_id_str,
                "title": v.title,
                "program_name": v.program.name if v.program else "",
                "published_at": v.published_at.isoformat() if v.published_at else None,
                "total_comments": overview["total_comments"],
                "valid_comments": overview["valid_comments"],
                "noise_rate": overview["noise_rate"],
                "top_topic": topics[0]["topic"] if topics else None,
                "stance_breakdown": {s["stance"]: s["count"] for s in stances},
            }
        )

    return result


def get_data_quality_analytics(
    db: Session,
    *,
    program_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Calculate data pipeline quality metrics."""
    overview = get_analytics_overview(
        db, program_id=program_id, channel_id=channel_id, start_date=start_date, end_date=end_date
    )

    stmt = (
        select(LayerPrediction.layer, func.avg(LayerPrediction.confidence).label("avg_conf"))
        .join(Comment, LayerPrediction.comment_id == Comment.id)
    )
    stmt = _apply_comment_filters(
        stmt, program_id=program_id, channel_id=channel_id, start_date=start_date, end_date=end_date
    )
    stmt = stmt.group_by(LayerPrediction.layer)
    rows = db.execute(stmt).all()

    conf_by_layer = {r.layer.value: round(r.avg_conf or 0.0, 4) for r in rows}

    return {
        "overview": overview,
        "average_confidence_by_layer": {
            "layer1": conf_by_layer.get("layer1", 0.0),
            "layer2": conf_by_layer.get("layer2", 0.0),
            "layer4": conf_by_layer.get("layer4", 0.0),
        },
        "subissue_status": "ABSENT (permanently removed per research scope)",
    }


def get_evidence_analytics(db: Session, evidence_set_id: str) -> dict:
    """Calculate analytics for a specific evidence set."""
    es = get_evidence_set(db, evidence_set_id)
    if not es:
        return {}

    ev_items = es.evidence_items
    total_items = len(ev_items)

    topic_counts = {}
    stance_counts = {}

    for ev in ev_items:
        if ev.layer == LayerEnum.layer2 and ev.label:
            topic_counts[ev.label] = topic_counts.get(ev.label, 0) + 1
        elif ev.layer == LayerEnum.layer4 and ev.label:
            stance_counts[ev.label] = stance_counts.get(ev.label, 0) + 1

    return {
        "evidence_set_id": str(es.id),
        "retrieval_method": es.retrieval_method,
        "retrieved_at": es.retrieved_at.isoformat(),
        "total_evidence_items": total_items,
        "topic_distribution": topic_counts,
        "stance_distribution": stance_counts,
        "query_params": es.query_params,
    }


def get_faithfulness_analytics(
    db: Session,
    *,
    insight_id: Optional[str] = None,
    program_id: Optional[str] = None,
) -> dict:
    """Calculate faithfulness verification analytics across insights."""
    stmt = select(VerificationResult)
    if insight_id:
        try:
            stmt = stmt.where(VerificationResult.insight_id == uuid_mod.UUID(insight_id))
        except ValueError:
            return {}
    elif program_id:
        stmt = (
            stmt.join(Insight, VerificationResult.insight_id == Insight.id)
            .where(Insight.program_id == uuid_mod.UUID(program_id))
        )

    results = db.execute(stmt).scalars().all()
    if not results:
        return {
            "total_verifications": 0,
            "mean_grounding_score": 0.0,
            "mean_claim_support_rate": 0.0,
            "mean_partial_support_rate": 0.0,
            "mean_unsupported_claim_rate": 0.0,
            "mean_contradiction_rate": 0.0,
            "mean_citation_precision": 0.0,
        }

    total = len(results)
    mean_grounding = sum(r.grounding_score for r in results) / total
    mean_csr = sum(r.claim_support_rate for r in results) / total
    mean_psr = sum(
        (r.verification_details_json.get("partial_support_rate", 0.0) if isinstance(r.verification_details_json, dict) else 0.0)
        for r in results
    ) / total
    mean_ucr = sum(r.unsupported_claim_rate for r in results) / total
    mean_cr = sum(r.contradiction_rate for r in results) / total
    mean_prec = sum(
        (r.verification_details_json.get("evidence_citation_precision", 0.0) if isinstance(r.verification_details_json, dict) else 0.0)
        for r in results
    ) / total

    return {
        "total_verifications": total,
        "mean_grounding_score": round(mean_grounding, 4),
        "mean_claim_support_rate": round(mean_csr, 4),
        "mean_partial_support_rate": round(mean_psr, 4),
        "mean_unsupported_claim_rate": round(mean_ucr, 4),
        "mean_contradiction_rate": round(mean_cr, 4),
        "mean_citation_precision": round(mean_prec, 4),
    }
