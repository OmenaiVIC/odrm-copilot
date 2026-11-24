"""create screening evidence Merkle chain

Revision ID: 0004_evidence_chain
Revises: 0003_public_good_whitelist
Create Date: 2026-11-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_evidence_chain"
down_revision: str | None = "0003_public_good_whitelist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("merkle_root", sa.String(length=64), nullable=False),
        sa.Column("leaf_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "anchor_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(merkle_root) = 64",
            name="ck_evidence_batches_merkle_root_length",
        ),
        sa.CheckConstraint(
            "leaf_count >= 1",
            name="ck_evidence_batches_leaf_count_positive",
        ),
        sa.CheckConstraint(
            "anchor_status IN ('pending', 'anchored_on_soroban', 'verified')",
            name="ck_evidence_batches_anchor_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_batches_created_at_id",
        "evidence_batches",
        ["created_at", "id"],
    )

    op.create_table(
        "screening_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("screening_id", sa.String(length=36), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("screening_hash", sa.String(length=64), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64",
            name="ck_screening_evidence_input_hash_length",
        ),
        sa.CheckConstraint(
            "length(output_hash) = 64",
            name="ck_screening_evidence_output_hash_length",
        ),
        sa.CheckConstraint(
            "length(screening_hash) = 64",
            name="ck_screening_evidence_screening_hash_length",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["evidence_batches.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_screening_evidence_screening_id",
        "screening_evidence",
        ["screening_id"],
    )
    op.create_index(
        "ix_screening_evidence_screening_hash",
        "screening_evidence",
        ["screening_hash"],
    )
    op.create_index(
        "ix_screening_evidence_batch_id",
        "screening_evidence",
        ["batch_id"],
    )
    op.create_index(
        "ix_screening_evidence_batch_leaf_order",
        "screening_evidence",
        ["batch_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_screening_evidence_batch_leaf_order",
        table_name="screening_evidence",
    )
    op.drop_index(
        "ix_screening_evidence_batch_id",
        table_name="screening_evidence",
    )
    op.drop_index(
        "ix_screening_evidence_screening_hash",
        table_name="screening_evidence",
    )
    op.drop_index(
        "ix_screening_evidence_screening_id",
        table_name="screening_evidence",
    )
    op.drop_table("screening_evidence")
    op.drop_index(
        "ix_evidence_batches_created_at_id",
        table_name="evidence_batches",
    )
    op.drop_table("evidence_batches")
