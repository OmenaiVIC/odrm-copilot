from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from odrm.auth.models import Base

EVIDENCE_BATCH_MAX_LEAVES = 100
ANCHOR_STATUSES: frozenset[str] = frozenset(
    {"pending", "anchored_on_soroban", "verified"}
)
AnchorStatus = Literal["pending", "anchored_on_soroban", "verified"]


class EvidenceBatch(Base):
    __tablename__ = "evidence_batches"
    __table_args__ = (
        CheckConstraint(
            "length(merkle_root) = 64",
            name="ck_evidence_batches_merkle_root_length",
        ),
        CheckConstraint(
            "leaf_count >= 1",
            name="ck_evidence_batches_leaf_count_positive",
        ),
        CheckConstraint(
            "anchor_status IN ('pending', 'anchored_on_soroban', 'verified')",
            name="ck_evidence_batches_anchor_status",
        ),
        Index("ix_evidence_batches_created_at_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)
    leaf_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    anchor_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        server_default="pending",
        nullable=False,
    )

    leaves: Mapped[list[ScreeningEvidence]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"EvidenceBatch(id={self.id!r}, leaf_count={self.leaf_count!r}, "
            f"anchor_status={self.anchor_status!r})"
        )


class ScreeningEvidence(Base):
    __tablename__ = "screening_evidence"
    __table_args__ = (
        CheckConstraint(
            "length(input_hash) = 64",
            name="ck_screening_evidence_input_hash_length",
        ),
        CheckConstraint(
            "length(output_hash) = 64",
            name="ck_screening_evidence_output_hash_length",
        ),
        CheckConstraint(
            "length(screening_hash) = 64",
            name="ck_screening_evidence_screening_hash_length",
        ),
        Index("ix_screening_evidence_screening_id", "screening_id"),
        Index("ix_screening_evidence_screening_hash", "screening_hash"),
        Index("ix_screening_evidence_batch_id", "batch_id"),
        Index(
            "ix_screening_evidence_batch_leaf_order",
            "batch_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    screening_id: Mapped[str] = mapped_column(String(36), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    screening_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evidence_batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    batch: Mapped[EvidenceBatch] = relationship(back_populates="leaves")

    def __repr__(self) -> str:
        return (
            f"ScreeningEvidence(id={self.id!r}, screening_id={self.screening_id!r}, "
            f"batch_id={self.batch_id!r})"
        )
