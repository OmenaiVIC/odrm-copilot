from __future__ import annotations

from odrm.auth.models import User
from odrm.whitelist.models import WhitelistStatus
from odrm.whitelist.repository import (
    ApplyOutcome,
    WhitelistApplicationNotFoundError,
    WhitelistApplicationRecord,
    WhitelistRepository,
)


class RoleNotEligibleError(Exception):
    """Raised when a user's current role cannot apply for public-good status."""


class AdminRequiredError(Exception):
    """Raised when a non-admin attempts an administrative whitelist action."""


class WhitelistService:
    def __init__(self, repository: WhitelistRepository) -> None:
        self._repository = repository

    def apply(self, user: User, reason: str) -> ApplyOutcome:
        if user.role in {"admin", "public_good"}:
            raise RoleNotEligibleError("This role cannot apply for public-good status.")
        return self._repository.apply(user.id, reason)

    def get_for_user(self, user: User) -> WhitelistApplicationRecord:
        application = self._repository.get_for_user(user.id)
        if application is None:
            raise WhitelistApplicationNotFoundError("Whitelist application not found.")
        return application

    def list_applications(
        self,
        actor: User,
        status: WhitelistStatus | None = None,
    ) -> list[WhitelistApplicationRecord]:
        self._ensure_admin(actor)
        return self._repository.list_all(status)

    def approve(
        self,
        actor: User,
        application_id: str,
    ) -> WhitelistApplicationRecord:
        self._ensure_admin(actor)
        return self._repository.approve(application_id)

    def reject(
        self,
        actor: User,
        application_id: str,
        decision_reason: str,
    ) -> WhitelistApplicationRecord:
        self._ensure_admin(actor)
        return self._repository.reject(application_id, decision_reason)

    @staticmethod
    def _ensure_admin(actor: User) -> None:
        if actor.role != "admin":
            raise AdminRequiredError("Admin role required.")