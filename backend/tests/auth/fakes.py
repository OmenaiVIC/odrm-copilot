from __future__ import annotations

from odrm.auth.models import User


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    def add(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        return next(
            (user for user in self.users.values() if user.email == normalized),
            None,
        )

    def get_by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: str = "engineer",
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        return self.add(user)

    def list_all(self) -> list[User]:
        return sorted(self.users.values(), key=lambda user: user.email)

    def ping(self) -> bool:
        return True


class RecordingHasher:
    def __init__(self, *, valid: bool = True) -> None:
        self.valid = valid
        self.verify_calls: list[tuple[str, str]] = []
        self.dummy_calls = 0

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        self.verify_calls.append((password, password_hash))
        return self.valid

    def verify_dummy(self, password: str) -> bool:
        self.dummy_calls += 1
        return False
