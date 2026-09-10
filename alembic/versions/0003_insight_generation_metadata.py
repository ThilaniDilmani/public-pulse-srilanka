"""Add generation metadata columns to insights table — Phase 9.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-08 17:35:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers used by Alembic.
revision: str = "0003"
down_revision: str = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB() if is_postgres else sa.JSON()

    # 1. Add generation metadata columns to insights table
    op.add_column(
        "insights",
        sa.Column(
            "generation_status",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("insights", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("insights", sa.Column("llm_provider", sa.String(64), nullable=True))
    op.add_column("insights", sa.Column("llm_model", sa.String(128), nullable=True))
    op.add_column("insights", sa.Column("prompt_version", sa.String(32), nullable=True))
    op.add_column(
        "insights",
        sa.Column("generation_params_json", json_type, nullable=True),
    )

    # 2. Add indexes and unique constraint
    op.create_index(
        "ix_insights_evidence_set_id", "insights", ["evidence_set_id"]
    )
    op.create_index(
        "ix_insights_generation_status", "insights", ["generation_status"]
    )
    op.create_unique_constraint(
        "uq_insights_evidence_set_type",
        "insights",
        ["evidence_set_id", "insight_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_insights_evidence_set_type", "insights", type_="unique"
    )
    op.drop_index("ix_insights_generation_status", table_name="insights")
    op.drop_index("ix_insights_evidence_set_id", table_name="insights")
    op.drop_column("insights", "generation_params_json")
    op.drop_column("insights", "prompt_version")
    op.drop_column("insights", "llm_model")
    op.drop_column("insights", "llm_provider")
    op.drop_column("insights", "error_message")
    op.drop_column("insights", "generation_status")
