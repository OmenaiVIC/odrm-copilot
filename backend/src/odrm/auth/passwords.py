from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

_DUMMY_PASSWORD = "odrm-dummy-password-for-timing-equalization"


class PasswordHasher:
    """Argon2id password hashing with a constant-work verification fallback."""

    def __init__(self, password_hash: PasswordHash | None = None) -> None:
        self._password_hash = password_hash or PasswordHash.recommended()
        self._dummy_hash: str | None = None

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, hashed_password: str) -> bool:
        try:
            return self._password_hash.verify(password, hashed_password)
        except (UnknownHashError, ValueError, TypeError):
            return False

    def verify_dummy(self, password: str) -> None:
        if self._dummy_hash is None:
            self._dummy_hash = self.hash(_DUMMY_PASSWORD)
        self.verify(password, self._dummy_hash)
