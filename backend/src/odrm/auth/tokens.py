from __future__ import annotations

import time
from collections.abc import Callable
from uuid import uuid4

import jwt
from pydantic import BaseModel, ConfigDict, ValidationError

from odrm.core.config import Settings

_REQUIRED_CLAIMS = ("iss", "aud", "iat", "exp", "jti", "sub", "email", "role")


class TokenError(Exception):
    """Raised when a bearer token cannot be trusted."""


class TokenClaims(BaseModel):
    model_config = ConfigDict(frozen=True)

    iss: str
    aud: str
    iat: int
    exp: int
    jti: str
    sub: str
    email: str
    role: str


class TokenService:
    def __init__(
        self,
        settings: Settings,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._secret = settings.jwt_secret.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience
        self._access_token_minutes = settings.jwt_access_token_minutes
        self._clock = clock or time.time

    def issue_access_token(self, *, user_id: str, email: str, role: str) -> str:
        issued_at = int(self._clock())
        payload = {
            "iss": self._issuer,
            "aud": self._audience,
            "iat": issued_at,
            "exp": issued_at + self._access_token_minutes * 60,
            "jti": str(uuid4()),
            "sub": user_id,
            "email": email,
            "role": role,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "require": list(_REQUIRED_CLAIMS),
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
        except jwt.PyJWTError as exc:
            raise TokenError("Invalid authentication token.") from exc

        try:
            claims = TokenClaims.model_validate(payload)
        except ValidationError as exc:
            raise TokenError("Invalid authentication token.") from exc

        now = int(self._clock())
        if claims.exp <= now:
            raise TokenError("Authentication token has expired.")
        if claims.iat > now + 60:
            raise TokenError("Authentication token is not yet valid.")
        return claims
