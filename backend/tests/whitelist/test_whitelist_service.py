from __future__ import annotations

import pytest

from odrm.auth.models import User
from odrm.whitelist.repository import (
    WhitelistApplicationAlreadyApprovedError,
    WhitelistApplicationExistsError,
    WhitelistApplicationNotFoundError,
    WhitelistApplicationNotPendingError,
)
from odrm.whitelist.service import (
    AdminRequiredError,
    RoleNotEligibleError,
    WhitelistService,
)
from tests.auth.fakes import InMemoryUserRepository
from tests.whitelist.fakes import InMemoryWhitelistRepository


def add_user(
    users: InMemoryUserRepository,
    *,
    user_id: str,
    email: str,
    role: str = "commercial",
) -> User:
    user = User(
        id=user_id,
        email=email,
        password_hash="hash",
        role=role,
        is_active=True,
    )
    return users.add(user)


@pytest.fixture()
def users() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture()
def repository(users: InMemoryUserRepository) -> InMemoryWhitelistRepository:
    return InMemoryWhitelistRepository(users)


@pytest.fixture()
def service(repository: InMemoryWhitelistRepository) -> WhitelistService:
    return WhitelistService(repository)


@pytest.mark.parametrize("role", ["commercial", "viewer"])
def test_eligible_roles_can_apply(
    users: InMemoryUserRepository,
    service: WhitelistService,
    role: str,
) -> None:
    user = add_user(
        users,
        user_id=f"user-{role}",
        email=f"{role}@example.com",
        role=role,
    )
    outcome = service.apply(user, "I work with carbon brokers.")
    assert outcome.created is True
    assert outcome.application.status == "pending"
    assert outcome.application.user_id == user.id
    assert outcome.application.user_email == user.email
    assert outcome.application.reason == "I work with carbon brokers."
    assert outcome.application.decision_reason is None


@pytest.mark.parametrize("role", ["admin", "public_good"])
def test_ineligible_roles_cannot_apply(
    users: InMemoryUserRepository,
    repository: InMemoryWhitelistRepository,
    service: WhitelistService,
    role: str,
) -> None:
    user = add_user(
        users,
        user_id=f"user-{role}",
        email=f"{role}@example.com",
        role=role,
    )
    with pytest.raises(RoleNotEligibleError):
        service.apply(user, "I would like public-good status.")
    assert repository.get_for_user(user.id) is None


def test_pending_application_cannot_be_submitted_twice(
    users: InMemoryUserRepository,
    service: WhitelistService,
) -> None:
    user = add_user(
        users,
        user_id="user-commercial",
        email="applicant@example.com",
    )
    service.apply(user, "First application.")
    with pytest.raises(WhitelistApplicationExistsError):
        service.apply(user, "Second application.")


def test_rejected_application_reopens_with_new_reason(
    users: InMemoryUserRepository,
    service: WhitelistService,
) -> None:
    applicant = add_user(users, user_id="user-applicant", email="applicant@example.com")
    admin = add_user(users, user_id="user-admin", email="admin@example.com", role="admin")
    outcome = service.apply(applicant, "Initial details.")
    service.reject(admin, outcome.application.id, "Registration number missing.")
    reopened = service.apply(applicant, "Updated details with registration.")
    assert reopened.created is False
    assert reopened.application.id == outcome.application.id
    assert reopened.application.status == "pending"
    assert reopened.application.reason == "Updated details with registration."
    assert reopened.application.decision_reason is None


def test_approval_changes_role_and_blocks_a_second_decision(
    users: InMemoryUserRepository,
    service: WhitelistService,
) -> None:
    applicant = add_user(users, user_id="user-applicant", email="applicant@example.com")
    admin = add_user(users, user_id="user-admin", email="admin@example.com", role="admin")
    outcome = service.apply(applicant, "Valid application.")
    approved = service.approve(admin, outcome.application.id)
    assert approved.status == "approved"
    assert applicant.role == "public_good"
    with pytest.raises(WhitelistApplicationNotPendingError):
        service.approve(admin, outcome.application.id)
    with pytest.raises(WhitelistApplicationNotPendingError):
        service.reject(admin, outcome.application.id, "Too late.")


def test_approved_application_still_conflicts_when_role_has_changed(
    users: InMemoryUserRepository,
    service: WhitelistService,
) -> None:
    applicant = add_user(users, user_id="user-applicant", email="applicant@example.com")
    admin = add_user(users, user_id="user-admin", email="admin@example.com", role="admin")
    outcome = service.apply(applicant, "Valid application.")
    service.approve(admin, outcome.application.id)
    applicant.role = "commercial"
    with pytest.raises(WhitelistApplicationAlreadyApprovedError):
        service.apply(applicant, "Reapply after a role change.")


def test_rejection_stores_reason_and_preserves_role(
    users: InMemoryUserRepository,
    service: WhitelistService,
) -> None:
    applicant = add_user(users, user_id="user-applicant", email="applicant@example.com")
    admin = add_user(users, user_id="user-admin", email="admin@example.com", role="admin")
    outcome = service.apply(applicant, "Original reason.")
    rejected = service.reject(admin, outcome.application.id, "Please provide a company registration number.")
    assert rejected.status == "rejected"
    assert rejected.reason == "Original reason."
    assert rejected.decision_reason == "Please provide a company registration number."
    assert applicant.role == "commercial"


def test_non_admin_cannot_list_or_decide(
    users: InMemoryUserRepository,
    service: WhitelistService,
) -> None:
    applicant = add_user(users, user_id="user-applicant", email="applicant@example.com")
    outcome = service.apply(applicant, "Valid application.")
    with pytest.raises(AdminRequiredError):
        service.list_applications(applicant)
    with pytest.raises(AdminRequiredError):
        service.approve(applicant, outcome.application.id)
    with pytest.raises(AdminRequiredError):
        service.reject(applicant, outcome.application.id, "Not allowed.")


def test_get_for_user_requires_an_application(
    users: InMemoryUserRepository,
    service: WhitelistService,
) -> None:
    user = add_user(users, user_id="user-commercial", email="applicant@example.com")
    with pytest.raises(WhitelistApplicationNotFoundError):
        service.get_for_user(user)


def test_admin_list_filters_by_status(
    users: InMemoryUserRepository,
    service: WhitelistService,
) -> None:
    first = add_user(users, user_id="user-first", email="first@example.com")
    second = add_user(users, user_id="user-second", email="second@example.com")
    admin = add_user(users, user_id="user-admin", email="admin@example.com", role="admin")
    first_outcome = service.apply(first, "First application.")
    service.apply(second, "Second application.")
    service.approve(admin, first_outcome.application.id)
    pending = service.list_applications(admin, "pending")
    approved = service.list_applications(admin, "approved")
    assert [record.user_email for record in pending] == [second.email]
    assert [record.user_email for record in approved] == [first.email]