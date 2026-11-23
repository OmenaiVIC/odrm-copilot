from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from odrm.auth.dependencies import get_current_user, require_admin
from odrm.auth.models import User
from odrm.whitelist.models import WhitelistStatus
from odrm.whitelist.repository import (
    WhitelistApplicationAlreadyApprovedError,
    WhitelistApplicationExistsError,
    WhitelistApplicationNotFoundError,
    WhitelistApplicationNotPendingError,
    WhitelistApplicationRecord,
)
from odrm.whitelist.schemas import (
    WhitelistApplicationListResponse,
    WhitelistApplicationPublic,
    WhitelistApplyRequest,
    WhitelistRejectRequest,
)
from odrm.whitelist.service import (
    AdminRequiredError,
    RoleNotEligibleError,
    WhitelistService,
)

router = APIRouter(
    prefix="/whitelist",
    tags=["whitelist"],
    dependencies=[Depends(get_current_user)],
)


def _service(request: Request) -> WhitelistService:
    service: WhitelistService = request.app.state.whitelist_service
    return service


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _to_public(
    record: WhitelistApplicationRecord,
) -> WhitelistApplicationPublic:
    return WhitelistApplicationPublic.model_validate(record)


@router.post("/apply", response_model=WhitelistApplicationPublic)
def apply_for_whitelist(
    payload: WhitelistApplyRequest,
    request: Request,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
) -> WhitelistApplicationPublic:
    try:
        outcome = _service(request).apply(user, payload.reason)
    except RoleNotEligibleError as exc:
        raise _http_error(
            status.HTTP_400_BAD_REQUEST,
            "ROLE_NOT_ELIGIBLE",
            str(exc),
        ) from exc
    except WhitelistApplicationExistsError as exc:
        raise _http_error(
            status.HTTP_409_CONFLICT,
            "APPLICATION_EXISTS",
            str(exc),
        ) from exc
    except WhitelistApplicationAlreadyApprovedError as exc:
        raise _http_error(
            status.HTTP_409_CONFLICT,
            "APPLICATION_ALREADY_APPROVED",
            str(exc),
        ) from exc

    response.status_code = (
        status.HTTP_201_CREATED if outcome.created else status.HTTP_200_OK
    )
    return _to_public(outcome.application)


@router.get("/application", response_model=WhitelistApplicationPublic)
def get_my_whitelist_application(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> WhitelistApplicationPublic:
    try:
        record = _service(request).get_for_user(user)
    except WhitelistApplicationNotFoundError as exc:
        raise _http_error(
            status.HTTP_404_NOT_FOUND,
            "APPLICATION_NOT_FOUND",
            str(exc),
        ) from exc
    return _to_public(record)


@router.get("/applications", response_model=WhitelistApplicationListResponse)
def list_whitelist_applications(
    request: Request,
    admin: Annotated[User, Depends(require_admin)],
    status_filter: Annotated[
        WhitelistStatus | None,
        Query(alias="status"),
    ] = None,
) -> WhitelistApplicationListResponse:
    try:
        records = _service(request).list_applications(admin, status_filter)
    except AdminRequiredError as exc:
        raise _http_error(
            status.HTTP_403_FORBIDDEN,
            "FORBIDDEN",
            str(exc),
        ) from exc

    items = [_to_public(record) for record in records]
    return WhitelistApplicationListResponse(items=items, total=len(items))


@router.post(
    "/applications/{application_id}/approve",
    response_model=WhitelistApplicationPublic,
)
def approve_whitelist_application(
    application_id: str,
    request: Request,
    admin: Annotated[User, Depends(require_admin)],
) -> WhitelistApplicationPublic:
    try:
        record = _service(request).approve(admin, application_id)
    except WhitelistApplicationNotFoundError as exc:
        raise _http_error(
            status.HTTP_404_NOT_FOUND,
            "APPLICATION_NOT_FOUND",
            str(exc),
        ) from exc
    except WhitelistApplicationNotPendingError as exc:
        raise _http_error(
            status.HTTP_409_CONFLICT,
            "APPLICATION_NOT_PENDING",
            str(exc),
        ) from exc
    except AdminRequiredError as exc:
        raise _http_error(
            status.HTTP_403_FORBIDDEN,
            "FORBIDDEN",
            str(exc),
        ) from exc
    return _to_public(record)


@router.post(
    "/applications/{application_id}/reject",
    response_model=WhitelistApplicationPublic,
)
def reject_whitelist_application(
    application_id: str,
    payload: WhitelistRejectRequest,
    request: Request,
    admin: Annotated[User, Depends(require_admin)],
) -> WhitelistApplicationPublic:
    try:
        record = _service(request).reject(
            admin,
            application_id,
            payload.reason,
        )
    except WhitelistApplicationNotFoundError as exc:
        raise _http_error(
            status.HTTP_404_NOT_FOUND,
            "APPLICATION_NOT_FOUND",
            str(exc),
        ) from exc
    except WhitelistApplicationNotPendingError as exc:
        raise _http_error(
            status.HTTP_409_CONFLICT,
            "APPLICATION_NOT_PENDING",
            str(exc),
        ) from exc
    except AdminRequiredError as exc:
        raise _http_error(
            status.HTTP_403_FORBIDDEN,
            "FORBIDDEN",
            str(exc),
        ) from exc
    return _to_public(record)