"""SQLAlchemy ORM models for Public Pulse.

Active architecture: Layer 1 → Layer 2 + Layer 4.
The sub-issue classification layer (formerly between Layer 2 and Layer 4)
has been permanently removed — see docs/taxonomy.md for the documented
research-scope decision. The numbering gap is intentional.

Hierarchy:
    channels → programs → videos → comments → layer_predictions
                                             → annotations
                                             → evidence
    model_versions → layer_predictions
    programs → insights
    pipeline_runs (standalone audit log)

Text input contract (enforced by storing both columns):
    comments.text_raw:   original scraped text — Layer 1 input
    comments.text_clean: output of clean_text() — Layer 2 / Layer 4 input
    These must never be merged into a single field.

Type compatibility note:
    Models use sqlalchemy.Uuid (generic) and JSON (not PostgreSQL-specific
    JSONB) so that Base.metadata.create_all() works against SQLite for tests.
    The Alembic migration (alembic/versions/0001_initial_schema.py) uses
    native JSONB for PostgreSQL production columns.

Enum type note:
    All SAEnum columns use create_type=False — the PostgreSQL enum types
    (layer_enum, processing_status_enum, pipeline_run_status_enum) are
    created explicitly in the Alembic migration, not via create_all().
"""

import enum
import uuid
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Declarative base shared by all Public Pulse ORM models."""


# ---------------------------------------------------------------------------
# Python Enum definitions
# ---------------------------------------------------------------------------


class LayerEnum(str, enum.Enum):
    """Active classification layers.

    The sub-issue classification layer (formerly between Layer 2 and Layer 4)
    was permanently removed as a documented research-scope decision.
    The numbering gap (1, 2, 4) is preserved to match the research record.
    """

    layer1 = "layer1"
    layer2 = "layer2"
    layer4 = "layer4"
    # The removed sub-issue layer MUST NOT be added here



class ProcessingStatusEnum(str, enum.Enum):
    pending = "pending"      # comment ingested, not yet scored
    scored = "scored"        # all applicable layers predicted
    error = "error"          # pipeline error during scoring
    noise_exit = "noise_exit"  # Layer 1 classified as NOISE; L2/L4 not run


class PipelineRunStatusEnum(str, enum.Enum):
    running = "running"
    success = "success"
    error = "error"


# ---------------------------------------------------------------------------
# Shared type helpers (create_type=False: Alembic owns enum type creation)
# ---------------------------------------------------------------------------


def _layer_col_type() -> SAEnum:
    """SAEnum for the layer discriminator column.

    Values: 'layer1', 'layer2', 'layer4' only — the sub-issue layer is absent.
    create_type=False: the 'layer_enum' PostgreSQL type is created in the
    Alembic migration, not by SQLAlchemy's create_all().
    """

    return SAEnum(
        LayerEnum,
        name="layer_enum",
        values_callable=lambda obj: [e.value for e in obj],
        create_type=False,
    )


def _processing_status_col_type() -> SAEnum:
    return SAEnum(
        ProcessingStatusEnum,
        name="processing_status_enum",
        values_callable=lambda obj: [e.value for e in obj],
        create_type=False,
    )


def _pipeline_run_status_col_type() -> SAEnum:
    return SAEnum(
        PipelineRunStatusEnum,
        name="pipeline_run_status_enum",
        values_callable=lambda obj: [e.value for e in obj],
        create_type=False,
    )


# ---------------------------------------------------------------------------
# Table: channels
# ---------------------------------------------------------------------------


class Channel(Base):
    """A YouTube channel that hosts one or more monitored programs.

    Multiple programs may share the same channel — channels and programs
    are separate entities and must never be merged into one table.
    """

    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    youtube_channel_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subscriber_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    programs: Mapped[List["Program"]] = relationship(
        "Program", back_populates="channel"
    )

    def __repr__(self) -> str:
        return f"<Channel name={self.name!r} youtube_channel_id={self.youtube_channel_id!r}>"


# ---------------------------------------------------------------------------
# Table: programs
# ---------------------------------------------------------------------------


class Program(Base):
    """A monitored TV / YouTube program, associated with a channel.

    program_type is intentionally nullable — the authoritative classification
    of the 14 target programs has not yet been decided. Do NOT populate with
    invented values; leave NULL until an authoritative list is agreed on.
    """

    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(32), nullable=False, default="youtube", server_default="youtube"
    )
    # Nullable by design — program type not yet authoritatively defined.
    program_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    channel: Mapped["Channel"] = relationship("Channel", back_populates="programs")
    videos: Mapped[List["Video"]] = relationship("Video", back_populates="program")
    insights: Mapped[List["Insight"]] = relationship(
        "Insight", back_populates="program"
    )

    __table_args__ = (Index("ix_programs_channel_id", "channel_id"),)

    def __repr__(self) -> str:
        return f"<Program name={self.name!r} channel_id={self.channel_id!r}>"


# ---------------------------------------------------------------------------
# Table: videos
# ---------------------------------------------------------------------------


class Video(Base):
    """A YouTube video belonging to a monitored program."""

    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("programs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    youtube_video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_live: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    program: Mapped["Program"] = relationship("Program", back_populates="videos")
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="video",
        foreign_keys="Comment.video_id",
    )

    __table_args__ = (
        Index("ix_videos_program_published", "program_id", "published_at"),
        Index("ix_videos_published_at", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<Video youtube_video_id={self.youtube_video_id!r}>"


# ---------------------------------------------------------------------------
# Table: comments
# ---------------------------------------------------------------------------


class Comment(Base):
    """A YouTube comment scraped from a monitored video.

    Both text_raw and text_clean MUST be stored per comment:
        text_raw   — original scraped text; fed to Layer 1 (no cleaning)
        text_clean — output of clean_text(); fed to Layer 2 and Layer 4

    These fields must never be merged. See docs/taxonomy.md §Preprocessing.
    """

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("videos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Idempotency key: the scraper uses this to avoid re-inserting the same comment.
    youtube_comment_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )
    author_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Layer 1 input: original text, no preprocessing applied
    text_raw: Mapped[str] = mapped_column(Text, nullable=False)
    # Layer 2 / Layer 4 input: output of clean_text() preprocessing
    text_clean: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    reply_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_reply: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Optional reply threading — parent_comment_id is NULL for top-level comments.
    # Reply-thread processing logic is NOT part of Phase 5.
    parent_comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,
    )
    processing_status: Mapped[ProcessingStatusEnum] = mapped_column(
        _processing_status_col_type(),
        nullable=False,
        default=ProcessingStatusEnum.pending,
        server_default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    video: Mapped["Video"] = relationship(
        "Video",
        back_populates="comments",
        foreign_keys="[Comment.video_id]",
    )
    parent: Mapped[Optional["Comment"]] = relationship(
        "Comment",
        back_populates="replies",
        foreign_keys="[Comment.parent_comment_id]",
        remote_side="Comment.id",
    )
    replies: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="parent",
        foreign_keys="[Comment.parent_comment_id]",
    )
    predictions: Mapped[List["LayerPrediction"]] = relationship(
        "LayerPrediction", back_populates="comment"
    )
    annotations: Mapped[List["Annotation"]] = relationship(
        "Annotation", back_populates="comment"
    )
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="comment"
    )

    __table_args__ = (
        Index("ix_comments_video_id", "video_id"),
        Index("ix_comments_processing_status", "processing_status"),
        Index("ix_comments_posted_at", "posted_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Comment youtube_comment_id={self.youtube_comment_id!r} "
            f"status={self.processing_status!r}>"
        )


# ---------------------------------------------------------------------------
# Table: model_versions
# ---------------------------------------------------------------------------


class ModelVersion(Base):
    """A trained model checkpoint for one of the three active layers.

    layer must be one of 'layer1', 'layer2', 'layer4' — the removed
    sub-issue layer is not a valid value.

    At most one ModelVersion per layer may have is_active=True. This is
    enforced by the PostgreSQL partial unique index created in the Alembic
    migration (UNIQUE(layer) WHERE is_active = TRUE). The application-level
    repository also enforces this before setting is_active=True.
    """

    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    layer: Mapped[LayerEnum] = mapped_column(_layer_col_type(), nullable=False)
    checkpoint_ref: Mapped[str] = mapped_column(Text, nullable=False)
    base_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    trained_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    best_metric_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    best_metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Full classification report / training metadata stored as JSON.
    # In PostgreSQL production, the Alembic migration creates this as JSONB.
    metrics_json: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    predictions: Mapped[List["LayerPrediction"]] = relationship(
        "LayerPrediction", back_populates="model_version"
    )

    # NOTE: The partial unique index (UNIQUE(layer) WHERE is_active = TRUE)
    # is created by the Alembic migration only — it cannot be expressed
    # portably in __table_args__ without breaking SQLite-based tests.

    def __repr__(self) -> str:
        return (
            f"<ModelVersion layer={self.layer!r} "
            f"checkpoint_ref={self.checkpoint_ref!r} active={self.is_active}>"
        )


# ---------------------------------------------------------------------------
# Table: layer_predictions
# ---------------------------------------------------------------------------


class LayerPrediction(Base):
    """A single layer's prediction for a single comment.

    Expected rows per comment:
        NOISE comment: 1 row (layer1 only)
        VALID comment: 3 rows (layer1 + layer2 + layer4)

    Do NOT insert placeholder layer2/layer4 rows for NOISE comments.

    layer must be 'layer1', 'layer2', or 'layer4' — the sub-issue layer is invalid.
    The SAEnum constraint enforces this at the SQLAlchemy/Python level.
    """

    __tablename__ = "layer_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    layer: Mapped[LayerEnum] = mapped_column(_layer_col_type(), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    label_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    comment: Mapped["Comment"] = relationship("Comment", back_populates="predictions")
    model_version: Mapped["ModelVersion"] = relationship(
        "ModelVersion", back_populates="predictions"
    )

    __table_args__ = (
        UniqueConstraint(
            "comment_id",
            "layer",
            "model_version_id",
            name="uq_layer_predictions_comment_layer_version",
        ),
        Index("ix_layer_predictions_comment_layer", "comment_id", "layer"),
        Index(
            "ix_layer_predictions_layer_label_time", "layer", "label", "predicted_at"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<LayerPrediction layer={self.layer!r} "
            f"label={self.label!r} confidence={self.confidence:.4f}>"
        )


# ---------------------------------------------------------------------------
# Table: pipeline_runs
# ---------------------------------------------------------------------------


class PipelineRun(Base):
    """Audit log for batch inference and scraping pipeline executions."""

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[PipelineRunStatusEnum] = mapped_column(
        _pipeline_run_status_col_type(), nullable=False
    )
    comments_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comments_scored: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comments_noise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_pipeline_runs_started_at", "started_at"),)

    def __repr__(self) -> str:
        return f"<PipelineRun run_type={self.run_type!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Table: annotations
# ---------------------------------------------------------------------------


class Annotation(Base):
    """A human annotation label for a comment, per layer.

    layer must be 'layer1', 'layer2', or 'layer4' — sub-issue layer is invalid.
    One annotation per (comment, annotator, layer) is enforced by the
    UNIQUE constraint uq_annotations_comment_annotator_layer.
    """

    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
    )
    annotator: Mapped[str] = mapped_column(String(128), nullable=False)
    layer: Mapped[LayerEnum] = mapped_column(_layer_col_type(), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    comment: Mapped["Comment"] = relationship("Comment", back_populates="annotations")

    __table_args__ = (
        UniqueConstraint(
            "comment_id",
            "annotator",
            "layer",
            name="uq_annotations_comment_annotator_layer",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Annotation layer={self.layer!r} label={self.label!r} "
            f"annotator={self.annotator!r}>"
        )


# ---------------------------------------------------------------------------
# Table: evidence
# ---------------------------------------------------------------------------
# Table: evidence_sets
# ---------------------------------------------------------------------------


class EvidenceSet(Base):
    """A bounded collection of evidence items generated by a specific retrieval query.

    Provides complete provenance and reproducibility for downstream grounded insights (Phase 9).
    """

    __tablename__ = "evidence_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Full structured query parameters and filters stored as JSON/JSONB
    query_params: Mapped[Dict] = mapped_column(JSON, nullable=False)
    retrieval_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="hybrid_bm25_v1"
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    evidence_items: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="evidence_set", cascade="all, delete-orphan"
    )
    insights: Mapped[List["Insight"]] = relationship(
        "Insight", back_populates="evidence_set"
    )

    __table_args__ = (Index("ix_evidence_sets_retrieved_at", "retrieved_at"),)

    def __repr__(self) -> str:
        return f"<EvidenceSet id={self.id!r} method={self.retrieval_method!r}>"


# ---------------------------------------------------------------------------
# Table: evidence
# ---------------------------------------------------------------------------


class Evidence(Base):
    """A piece of evidence linking a comment to an evidence set or insight.

    Provides a persistence target for the future grounded-LLM system.

    layer, if set, must be 'layer1', 'layer2', or 'layer4' — sub-issue layer is invalid.
    """

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_set_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_sets.id", ondelete="CASCADE"),
        nullable=True,
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Optional — indicates which layer's output this evidence supports
    layer: Mapped[Optional[LayerEnum]] = mapped_column(
        _layer_col_type(), nullable=True
    )
    label: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rank: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    comment: Mapped["Comment"] = relationship("Comment", back_populates="evidence")
    evidence_set: Mapped[Optional["EvidenceSet"]] = relationship(
        "EvidenceSet", back_populates="evidence_items"
    )

    __table_args__ = (
        UniqueConstraint(
            "evidence_set_id",
            "comment_id",
            name="uq_evidence_evidence_set_comment",
        ),
        Index("ix_evidence_evidence_set_id", "evidence_set_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Evidence evidence_type={self.evidence_type!r} "
            f"layer={self.layer!r} rank={self.rank}>"
        )


# ---------------------------------------------------------------------------
# Table: insights
# ---------------------------------------------------------------------------


class Insight(Base):
    """An aggregated or generated insight, optionally tied to a program and evidence set.

    program_id is NULL for system-wide (cross-program) insights.
    evidence_set_id points to the grounded EvidenceSet used for generation.
    """

    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # NULL = system-wide insight (not tied to a specific program)
    program_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_set_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_sets.id", ondelete="SET NULL"),
        nullable=True,
    )
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # In PostgreSQL production, the migration creates this column as JSONB.
    payload_json: Mapped[Dict] = mapped_column(JSON, nullable=False)
    generation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    generation_params_json: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    program: Mapped[Optional["Program"]] = relationship(
        "Program", back_populates="insights"
    )
    evidence_set: Mapped[Optional["EvidenceSet"]] = relationship(
        "EvidenceSet", back_populates="insights"
    )

    __table_args__ = (
        UniqueConstraint(
            "evidence_set_id",
            "insight_type",
            name="uq_insights_evidence_set_type",
        ),
        Index("ix_insights_evidence_set_id", "evidence_set_id"),
        Index("ix_insights_generation_status", "generation_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Insight insight_type={self.insight_type!r} "
            f"status={self.generation_status!r}>"
        )


# ---------------------------------------------------------------------------
# Table: verification_results
# ---------------------------------------------------------------------------


class VerificationResult(Base):
    """An audit log of a faithfulness verification run over a generated insight."""

    __tablename__ = "verification_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    insight_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("insights.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    verifier_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="hybrid_nli_v1", server_default="hybrid_nli_v1"
    )
    verifier_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    grounding_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    claim_support_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unsupported_claim_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contradiction_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verification_details_json: Mapped[Dict] = mapped_column(JSON, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    insight: Mapped["Insight"] = relationship("Insight")
    evidence_set: Mapped["EvidenceSet"] = relationship("EvidenceSet")

    __table_args__ = (
        UniqueConstraint(
            "insight_id",
            "verifier_method",
            name="uq_verification_results_insight_method",
        ),
        Index("ix_verification_results_insight_id", "insight_id"),
        Index("ix_verification_results_evidence_set_id", "evidence_set_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<VerificationResult method={self.verifier_method!r} "
            f"CSR={self.claim_support_rate:.2f} CR={self.contradiction_rate:.2f}>"
        )


# ---------------------------------------------------------------------------
# Table: jobs
# ---------------------------------------------------------------------------


class JobRecord(Base):
    """Audit and tracking record for async background operations (Phase 11)."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending"
    )
    reference_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_jobs_status", "status"),)

    def __repr__(self) -> str:
        return f"<JobRecord type={self.job_type!r} status={self.status!r}>"


