from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from odrm.whitelist.models import WhitelistStatus
from odrm.whitelist.repository import (
    ApplyOutcome,
    WhitelistApplicationAlreadyApprovedError,
    WhitelistApplicationExistsError,
    WhitelistApplicationNotFoundError,
    WhitelistApplicationNotPendingError,
    WhitelistApplicationRecord,
)
from tests.auth.fakes import InMemoryUserRepository


class InMemoryWhitelistRepository:
    def __init__(self, users: InMemoryUserRepository) -> None:
        self.users = users
        self.applications: dict[str, WhitelistApplicationRecord] = {}

    def get_for_user(self, user_id: str) -> WhitelistApplicationRecord | None:
        for app in self.applications.values():
            if app.user_id == user_id:
                return app
        return None

    def get_by_id(self, application_id: str) -> WhitelistApplicationRecord | None:
        return self.applications.get(application_id)

    def list_all(
        self,
        status: WhitelistStatus | None = None,
    ) -> list[WhitelistApplicationRecord]:
        apps = list(self.applications.values())
        if status:
            apps = [a for a in apps if a.status == status]
        return sorted(apps, key=lambda a: a.created_at, reverse=True)

    def apply(self, user_id: str, reason: str) -> ApplyOutcome:
        user = self.users.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} does not exist.")

        existing = self.get_for_user(user_id)
        if existing:
            if existing.status == "pending":
                raise WhitelistApplicationExistsError("Already pending.")
            elif existing.status == "approved":
                raise WhitelistApplicationAlreadyApprovedError("Already approved.")
            else:
                # Reopen
                updated = WhitelistApplicationRecord(
                    id=existing.id,
                    user_id=existing.user_id,
                    user_email=user.email,
                    status="pending",
                    reason=reason,
                    decision_reason=None,
                    created_at=existing.created_at,
                )
                self.applications[existing.id] = updated
                return ApplyOutcome(application=updated, created=False)

        app_id = str(uuid4())
        new_app = WhitelistApplicationRecord(
            id=app_id,
            user_id=user_id,
            user_email=user.email,
            status="pending",
            reason=reason,
            decision_reason=None,
            created_at=datetime.now(UTC),
        )
        self.applications[app_id] = new_app
        return ApplyOutcome(application=new_app, created=True)

    def approve(self, application_id: str) -> WhitelistApplicationRecord:
        app = self.get_by_id(application_id)
        if not app:
            raise WhitelistApplicationNotFoundError("Not found.")
        if app.status != "pending":
            raise WhitelistApplicationNotPendingError("Not pending.")

        user = self.users.get_by_id(app.user_id)
        if user:
            user.role = "public_good"

        updated = WhitelistApplicationRecord(
            id=app.id,
            user_id=app.user_id,
            user_email=app.user_email,
            status="approved",
            reason=app.reason,
            decision_reason=app.decision_reason,
            created_at=app.created_at,
        )
        self.applications[app.id] = updated
        return updated

    def reject(
        self,
        application_id: str,
        decision_reason: str,
    ) -> WhitelistApplicationRecord:
        app = self.get_by_id(application_id)
        if not app:
            raise WhitelistApplicationNotFoundError("Not found.")
        if app.status != "pending":
            raise WhitelistApplicationNotPendingError("Not pending.")

        updated = WhitelistApplicationRecord(
            id=app.id,
            user_id=app.user_id,
            user_email=app.user_email,
            status="rejected",
            reason=app.reason,
            decision_reason=decision_reason,
            created_at=app.created_at,
        )
        self.applications[app.id] = updated
        return updated