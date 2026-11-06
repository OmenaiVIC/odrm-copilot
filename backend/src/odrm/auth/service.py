from __future__ import annotations

from odrm.auth.models import User
from odrm.auth.passwords import PasswordHasher
from odrm.auth.repository import UserRepository, normalize_email
from odrm.auth.tokens import TokenError, TokenService


class AuthenticationError(Exception):
    """Raised when credentials or a token cannot authenticate a user."""


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_service = token_service

    def authenticate(self, email: str, password: str) -> User:
        user = self._repository.get_by_email(normalize_email(email))
        if user is None:
            self._password_hasher.verify_dummy(password)
            raise AuthenticationError("Invalid email or password.")

        if not self._password_hasher.verify(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("Invalid email or password.")

        return user

    def issue_access_token(self, user: User) -> str:
        return self._token_service.issue_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )

    def resolve_access_token(self, token: str) -> User:
        try:
            claims = self._token_service.decode_access_token(token)
        except TokenError as exc:
            raise AuthenticationError("Authentication required.") from exc

        user = self._repository.get_by_id(claims.sub)
        if user is None or not user.is_active:
            raise AuthenticationError("Authentication required.")

        return user
