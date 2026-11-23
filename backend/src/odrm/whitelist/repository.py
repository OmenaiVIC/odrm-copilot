from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from odrm.auth.models import User
from odrm.whitelist.models import WhitelistApplication, WhitelistStatus


class WhitelistApplicationNotFoundError(Exception):
    """Raised when a whitelist application does not exist."""


class WhitelistApplicationNotPendingError(Exception):
    """Raised when a decision is attempted on a non-pending application."""


class WhitelistApplicationExistsError(Exception):
    """Raised when a user already has a pending whitelist application."""


class WhitelistApplicationAlreadyApprovedError(Exception):
    """Raised when a user already has an approved whitelist application."""


@dataclass(frozen=True)
class WhitelistApplicationRecord:
    id: str
    user_id: str
    user_email: str
    status: WhitelistStatus
    reason: str
    decision_reason: str | None
    created_at: datetime


@dataclass(frozen=True)
class ApplyOutcome:
    application: WhitelistApplicationRecord
    created: bool


class WhitelistRepository(Protocol):
    def get_for_user(self, user_id: str) -> WhitelistApplicationRecord | None: ...

    def get_by_id(self, application_id: str) -> WhitelistApplicationRecord | None: ...

    def list_all(
        self,
        status: WhitelistStatus | None = None,
    ) -> list[WhitelistApplicationRecord]: ...

    def apply(self, user_id: str, reason: str) -> ApplyOutcome: ...

    def approve(self, application_id: str) -> WhitelistApplicationRecord: ...

    def reject(
        self,
        application_id: str,
        decision_reason: str,
    ) -> WhitelistApplicationRecord: ...


def _to_record(application: WhitelistApplication) -> WhitelistApplicationRecord:
    return WhitelistApplicationRecord(
        id=application.id,
        user_id=application.user_id,
        user_email=application.user.email,
        status=cast(WhitelistStatus, application.status),
        reason=application.reason,
        decision_reason=application.decision_reason,
        created_at=application.created_at,
    )


class SqlAlchemyWhitelistRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_for_user(self, user_id: str) -> WhitelistApplicationRecord | None:
        with self._session_factory() as session:
            application = session.scalar(
                select(WhitelistApplication).where(
                    WhitelistApplication.user_id == user_id
                )
            )
            return _to_record(application) if application is not None else None

    def get_by_id(self, application_id: str) -> WhitelistApplicationRecord | None:
        with self._session_factory() as session:
            application = session.get(WhitelistApplication, application_id)
            return _to_record(application) if application is not None else None

    def list_all(
        self,
        status: WhitelistStatus | None = None,
    ) -> list[WhitelistApplicationRecord]:
        with self._session_factory() as session:
            statement = select(WhitelistApplication)
            if status is not None:
                statement = statement.where(
                    WhitelistApplication.status == status
                )
            statement = statement.order_by(
                WhitelistApplication.created_at.desc(),
                WhitelistApplication.id.asc(),
            )
            return [
                _to_record(application)
                for application in session.scalars(statement)
            ]

    def apply(self, user_id: str, reason: str) -> ApplyOutcome:
        with self._session_factory() as session:
            application = session.scalar(
                select(WhitelistApplication)
                .where(WhitelistApplication.user_id == user_id)
                .with_for_update()
            )

            if application is None:
                applicant = session.get(User, user_id)
                if applicant is None:
                    raise ValueError(f"Whitelist applicant {user_id!r} does not exist.")
                application = WhitelistApplication(
                    user=applicant,
                    reason=reason,
                )
                session.add(application)
                created = True
            elif application.status == "pending":
                raise WhitelistApplicationExistsError("A whitelist application is already pending.")
            elif application.status == "approved":
                raise WhitelistApplicationAlreadyApprovedError("The whitelist application is already approved.")
            else:
                application.status = "pending"
                application.reason = reason
                application.decision_reason = None
                created = False

            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise WhitelistApplicationExistsError("A whitelist application is already pending.") from exc

            session.refresh(application)
            return ApplyOutcome(
                application=_to_record(application),
                created=created,
            )

    def approve(self, application_id: str) -> WhitelistApplicationRecord:
        with self._session_factory() as session:
            application = session.scalar(
                select(WhitelistApplication)
                .where(WhitelistApplication.id == application_id)
                .with_for_update()
            )
            if application is None:
                raise WhitelistApplicationNotFoundError("Whitelist application not found.")
            if application.status != "pending":
                raise WhitelistApplicationNotPendingError("Whitelist application is not pending.")

            application.status = "approved"
            application.user.role = "public_good"
            session.commit()
            session.refresh(application)
            return _to_record(application)

    def reject(
        self,
        application_id: str,
        decision_reason: str,
    ) -> WhitelistApplicationRecord:
        with self._session_factory() as session:
            application = session.scalar(
                select(WhitelistApplication)
                .where(WhitelistApplication.id == application_id)
                .with_for_update()
            )
            if application is None:
                raise WhitelistApplicationNotFoundError("Whitelist application not found.")
            if application.status != "pending":
                raise WhitelistApplicationNotPendingError("Whitelist application is not pending.")

            application.status = "rejected"
            application.decision_reason = decision_reason
            session.commit()
            session.refresh(application)
            return _to_record(application)