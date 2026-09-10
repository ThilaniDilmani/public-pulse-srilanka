"""Add jobs table and performance indexes — Phase 11.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-08 19:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# Revision identifiers used by Alembic.
revision: str = "0005"
down_revision: str = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reference_id", sa.String(128), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Indexes
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index(
        "ix_layer_predictions_comment_id", "layer_predictions", ["comment_id"]
    )
    op.create_index(
        "ix_comments_video_posted_at", "comments", ["video_id", "posted_at"]
    )
    op.create_index("ix_insights_program_id", "insights", ["program_id"])


def downgrade() -> None:
    op.drop_index("ix_insights_program_id", table_name="insights")
    op.drop_index("ix_comments_video_posted_at", table_name="comments")
    op.drop_index("ix_layer_predictions_comment_id", table_name="layer_predictions")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
