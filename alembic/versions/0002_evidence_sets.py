"""Add evidence_sets table and link to evidence and insights — Phase 8.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-08 15:45:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers used by Alembic.
revision: str = "0002"
down_revision: str = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB() if is_postgres else sa.JSON()

    # 1. Create evidence_sets table
    op.create_table(
        "evidence_sets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("query_params", json_type, nullable=False),
        sa.Column(
            "retrieval_method",
            sa.String(64),
            nullable=False,
            server_default="hybrid_bm25_v1",
        ),
        sa.Column(
            "retrieved_at",
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
    )
    op.create_index("ix_evidence_sets_retrieved_at", "evidence_sets", ["retrieved_at"])

    # 2. Add columns and constraints to evidence table
    op.add_column(
        "evidence",
        sa.Column(
            "evidence_set_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("evidence_sets.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column("evidence", sa.Column("relevance_score", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("rank", sa.SmallInteger(), nullable=True))
    op.create_index(
        "ix_evidence_evidence_set_id", "evidence", ["evidence_set_id"]
    )
    op.create_unique_constraint(
        "uq_evidence_evidence_set_comment",
        "evidence",
        ["evidence_set_id", "comment_id"],
    )

    # 3. Add evidence_set_id to insights table
    op.add_column(
        "insights",
        sa.Column(
            "evidence_set_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("evidence_sets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("insights", "evidence_set_id")
    op.drop_constraint(
        "uq_evidence_evidence_set_comment", "evidence", type_="unique"
    )
    op.drop_index("ix_evidence_evidence_set_id", table_name="evidence")
    op.drop_column("evidence", "rank")
    op.drop_column("evidence", "relevance_score")
    op.drop_column("evidence", "evidence_set_id")
    op.drop_index("ix_evidence_sets_retrieved_at", table_name="evidence_sets")
    op.drop_table("evidence_sets")
