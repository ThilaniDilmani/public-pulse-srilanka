"""Add verification_results table — Phase 10.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-08 17:55:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers used by Alembic.
revision: str = "0004"
down_revision: str = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB() if is_postgres else sa.JSON()

    # 1. Create verification_results table
    op.create_table(
        "verification_results",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "insight_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("insights.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_set_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("evidence_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "verifier_method",
            sa.String(64),
            nullable=False,
            server_default="hybrid_nli_v1",
        ),
        sa.Column("verifier_model", sa.String(128), nullable=True),
        sa.Column("grounding_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("claim_support_rate", sa.Float(), nullable=False, default=0.0),
        sa.Column("unsupported_claim_rate", sa.Float(), nullable=False, default=0.0),
        sa.Column("contradiction_rate", sa.Float(), nullable=False, default=0.0),
        sa.Column("verification_details_json", json_type, nullable=False),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 2. Add indexes and unique constraint
    op.create_index(
        "ix_verification_results_insight_id",
        "verification_results",
        ["insight_id"],
    )
    op.create_index(
        "ix_verification_results_evidence_set_id",
        "verification_results",
        ["evidence_set_id"],
    )
    op.create_unique_constraint(
        "uq_verification_results_insight_method",
        "verification_results",
        ["insight_id", "verifier_method"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_verification_results_insight_method",
        "verification_results",
        type_="unique",
    )
    op.drop_index(
        "ix_verification_results_evidence_set_id",
        table_name="verification_results",
    )
    op.drop_index(
        "ix_verification_results_insight_id",
        table_name="verification_results",
    )
    op.drop_table("verification_results")
