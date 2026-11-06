from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from odrm.auth.models import User


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    role: str

    @classmethod
    def from_user(cls, user: User) -> UserPublic:
        return cls(id=user.id, email=user.email, role=user.role)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=1_024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic
