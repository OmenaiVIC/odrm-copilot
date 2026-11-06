from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from odrm.auth.dependencies import get_current_user
from odrm.auth.models import User
from odrm.auth.schemas import LoginRequest, LoginResponse, UserPublic
from odrm.auth.service import AuthenticationError, AuthService
from odrm.core.config import Settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
) -> LoginResponse:
    settings: Settings = request.app.state.settings
    auth_service: AuthService = request.app.state.auth_service
    try:
        user = auth_service.authenticate(payload.email, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password.",
            },
        ) from exc

    expires_in = settings.jwt_access_token_minutes * 60
    token = auth_service.issue_access_token(user)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=expires_in,
        path=settings.api_prefix,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserPublic.from_user(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> Response:
    settings: Settings = request.app.state.settings
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path=settings.api_prefix,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/me", response_model=UserPublic)
def me(
    request: Request,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
) -> UserPublic:
    response.headers["Cache-Control"] = "no-store"
    return UserPublic.from_user(user)
