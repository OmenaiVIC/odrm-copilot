from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from odrm.auth.models import User
from odrm.auth.service import AuthenticationError, AuthService
from odrm.core.config import Settings

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "UNAUTHORIZED",
            "message": "Authentication required.",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def _csrf_rejected() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "CSRF_ORIGIN_REJECTED",
            "message": "Request origin is not allowed.",
        },
    )


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[str, str] | None:
    authorization = request.headers.get("authorization")
    if authorization is not None:
        if (
            credentials is None
            or credentials.scheme.lower() != "bearer"
            or not credentials.credentials
        ):
            return None
        return credentials.credentials, "bearer"

    settings: Settings = request.app.state.settings
    cookie_token = request.cookies.get(settings.auth_cookie_name)
    if cookie_token:
        return cookie_token, "cookie"

    return None


def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> User:
    extracted = _extract_token(request, credentials)
    if extracted is None:
        raise _unauthorized()

    token, source = extracted
    settings: Settings = request.app.state.settings
    if source == "cookie" and request.method.upper() not in _SAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is None or origin not in settings.cors_origin_list:
            raise _csrf_rejected()

    auth_service: AuthService = request.app.state.auth_service
    try:
        return auth_service.resolve_access_token(token)
    except AuthenticationError as exc:
        raise _unauthorized() from exc
