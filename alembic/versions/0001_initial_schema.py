"""Initial database schema for Public Pulse — Phase 5.

Creates all 10 tables, PostgreSQL enum types, indexes, and
the partial unique index on model_versions (is_active per layer).

Active architecture: Layer 1 → Layer 2 + Layer 4.
Layer 3 has been permanently removed — it does not appear anywhere
in this migration.

Enum values:
    layer_enum:                layer1 | layer2 | layer4  (no layer3)
    processing_status_enum:    pending | scored | error | noise_exit
    pipeline_run_status_enum:  running | success | error

Table creation order (respects foreign key dependencies):
    1. channels
    2. programs          → channels
    3. model_versions
    4. pipeline_runs
    5. videos            → programs
    6. comments          → videos (self-ref parent_comment_id)
    7. layer_predictions → comments, model_versions
    8. annotations       → comments
    9. evidence          → comments
    10. insights         → programs

Downgrade drops in reverse order then drops enum types.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # ------------------------------------------------------------------
    # PostgreSQL custom enum types (created only on PostgreSQL)
    # ------------------------------------------------------------------
    if is_postgres:
        layer_enum = postgresql.ENUM(
            "layer1", "layer2", "layer4",
            name="layer_enum",
            create_type=True,
        )
        layer_enum.create(bind, checkfirst=True)

        processing_status_enum = postgresql.ENUM(
            "pending", "scored", "error", "noise_exit",
            name="processing_status_enum",
            create_type=True,
        )
        processing_status_enum.create(bind, checkfirst=True)

        pipeline_run_status_enum = postgresql.ENUM(
            "running", "success", "error",
            name="pipeline_run_status_enum",
            create_type=True,
        )
        pipeline_run_status_enum.create(bind, checkfirst=True)

    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    # ------------------------------------------------------------------
    # 1. channels
    # ------------------------------------------------------------------
    op.create_table(
        "channels",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("youtube_channel_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("channel_url", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("subscriber_count", sa.BigInteger, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("youtube_channel_id", name="uq_channels_youtube_channel_id"),
    )

    # ------------------------------------------------------------------
    # 2. programs
    # ------------------------------------------------------------------
    op.create_table(
        "programs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "channel_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("channels.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "platform", sa.String(32), nullable=False, server_default="youtube"
        ),
        sa.Column("program_type", sa.String(64), nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ------------------------------------------------------------------
    # 3. model_versions
    # ------------------------------------------------------------------
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "layer",
            postgresql.ENUM("layer1", "layer2", "layer4", name="layer_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("checkpoint_ref", sa.Text, nullable=False),
        sa.Column("base_model", sa.String(128), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("best_metric_name", sa.String(64), nullable=True),
        sa.Column("best_metric_value", sa.Float, nullable=True),
        sa.Column("metrics_json", json_type, nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ------------------------------------------------------------------
    # 4. pipeline_runs
    # ------------------------------------------------------------------
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("run_type", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "running", "success", "error",
                name="pipeline_run_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("comments_processed", sa.Integer, nullable=True),
        sa.Column("comments_scored", sa.Integer, nullable=True),
        sa.Column("comments_noise", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("triggered_by", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ------------------------------------------------------------------
    # 5. videos
    # ------------------------------------------------------------------
    op.create_table(
        "videos",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "program_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("programs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("youtube_video_id", sa.String(64), nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column(
            "is_live", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("comment_count", sa.Integer, nullable=True),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("youtube_video_id", name="uq_videos_youtube_video_id"),
    )

    # ------------------------------------------------------------------
    # 6. comments
    # ------------------------------------------------------------------
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "video_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("videos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("youtube_comment_id", sa.String(128), nullable=False),
        sa.Column("author_hash", sa.String(64), nullable=True),
        sa.Column("text_raw", sa.Text, nullable=False),
        sa.Column("text_clean", sa.Text, nullable=False),
        sa.Column(
            "like_count", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "reply_count", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "is_reply", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "parent_comment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("comments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "processing_status",
            postgresql.ENUM(
                "pending", "scored", "error", "noise_exit",
                name="processing_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "youtube_comment_id", name="uq_comments_youtube_comment_id"
        ),
    )

    # ------------------------------------------------------------------
    # 7. layer_predictions
    # ------------------------------------------------------------------
    op.create_table(
        "layer_predictions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "comment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "layer",
            postgresql.ENUM("layer1", "layer2", "layer4", name="layer_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("label_id", sa.SmallInteger, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column(
            "predicted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "comment_id",
            "layer",
            "model_version_id",
            name="uq_layer_predictions_comment_layer_version",
        ),
    )

    # ------------------------------------------------------------------
    # 8. annotations
    # ------------------------------------------------------------------
    op.create_table(
        "annotations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "comment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("annotator", sa.String(128), nullable=False),
        sa.Column(
            "layer",
            postgresql.ENUM("layer1", "layer2", "layer4", name="layer_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "comment_id",
            "annotator",
            "layer",
            name="uq_annotations_comment_annotator_layer",
        ),
    )

    # ------------------------------------------------------------------
    # 9. evidence
    # ------------------------------------------------------------------
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "comment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(64), nullable=False),
        sa.Column(
            "layer",
            postgresql.ENUM("layer1", "layer2", "layer4", name="layer_enum", create_type=False),
            nullable=True,
        ),
        sa.Column("label", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ------------------------------------------------------------------
    # 10. insights
    # ------------------------------------------------------------------
    op.create_table(
        "insights",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "program_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("programs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("insight_type", sa.String(64), nullable=False),
        sa.Column("period_start", sa.Date, nullable=True),
        sa.Column("period_end", sa.Date, nullable=True),
        sa.Column("payload_json", json_type, nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ------------------------------------------------------------------
    # Regular indexes
    # ------------------------------------------------------------------
    op.create_index("ix_programs_channel_id", "programs", ["channel_id"])
    op.create_index(
        "ix_videos_program_published", "videos", ["program_id", "published_at"]
    )
    op.create_index("ix_videos_published_at", "videos", ["published_at"])
    op.create_index("ix_comments_video_id", "comments", ["video_id"])
    op.create_index(
        "ix_comments_processing_status", "comments", ["processing_status"]
    )
    op.create_index("ix_comments_posted_at", "comments", ["posted_at"])
    op.create_index(
        "ix_layer_predictions_comment_layer",
        "layer_predictions",
        ["comment_id", "layer"],
    )
    op.create_index(
        "ix_layer_predictions_layer_label_time",
        "layer_predictions",
        ["layer", "label", "predicted_at"],
    )
    op.create_index(
        "ix_pipeline_runs_started_at", "pipeline_runs", ["started_at"]
    )

    # ------------------------------------------------------------------
    # Partial unique index (PostgreSQL only)
    # ------------------------------------------------------------------
    if is_postgres:
        op.create_index(
            "uix_model_versions_active_layer",
            "model_versions",
            ["layer"],
            unique=True,
            postgresql_where=sa.text("is_active = TRUE"),
        )



def downgrade() -> None:
    # Drop indexes first
    op.drop_index("uix_model_versions_active_layer", table_name="model_versions")
    op.drop_index("ix_pipeline_runs_started_at", table_name="pipeline_runs")
    op.drop_index(
        "ix_layer_predictions_layer_label_time", table_name="layer_predictions"
    )
    op.drop_index(
        "ix_layer_predictions_comment_layer", table_name="layer_predictions"
    )
    op.drop_index("ix_comments_posted_at", table_name="comments")
    op.drop_index("ix_comments_processing_status", table_name="comments")
    op.drop_index("ix_comments_video_id", table_name="comments")
    op.drop_index("ix_videos_published_at", table_name="videos")
    op.drop_index("ix_videos_program_published", table_name="videos")
    op.drop_index("ix_programs_channel_id", table_name="programs")

    # Drop tables in reverse dependency order
    op.drop_table("insights")
    op.drop_table("evidence")
    op.drop_table("annotations")
    op.drop_table("layer_predictions")
    op.drop_table("comments")
    op.drop_table("videos")
    op.drop_table("pipeline_runs")
    op.drop_table("model_versions")
    op.drop_table("programs")
    op.drop_table("channels")

    # Drop PostgreSQL enum types
    op.execute("DROP TYPE IF EXISTS pipeline_run_status_enum")
    op.execute("DROP TYPE IF EXISTS processing_status_enum")
    op.execute("DROP TYPE IF EXISTS layer_enum")
