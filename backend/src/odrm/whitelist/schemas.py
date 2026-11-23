from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from odrm.whitelist.models import WhitelistStatus


class WhitelistApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2_000)


class WhitelistRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2_000)


class WhitelistApplicationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    user_email: EmailStr
    status: WhitelistStatus
    reason: str
    decision_reason: str | None
    created_at: datetime


class WhitelistApplicationListResponse(BaseModel):
    items: list[WhitelistApplicationPublic]
    total: int = Field(ge=0)