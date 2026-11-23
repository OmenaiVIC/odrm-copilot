from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from odrm.auth.models import Base, User

WhitelistStatus = Literal["pending", "approved", "rejected"]
WHITELIST_STATUSES: frozenset[str] = frozenset({"pending", "approved", "rejected"})


class WhitelistApplication(Base):
    __tablename__ = "whitelist_applications"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_whitelist_applications_user_id"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_whitelist_applications_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped[User] = relationship(lazy="joined")

    def __repr__(self) -> str:
        return (
            f"WhitelistApplication(id={self.id!r}, user_id={self.user_id!r}, "
            f"status={self.status!r})"
        )