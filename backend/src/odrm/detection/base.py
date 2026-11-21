from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Hotspot(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    intensity_ppb: float = Field(ge=0)
    detected_at: datetime
    source: str


def _require_bbox_valid(
    bbox: tuple[float, float, float, float] | None,
) -> None:
    if bbox is None:
        return
    if len(bbox) != 4:
        raise ValueError(
            "bbox must contain exactly four values: "
            "(min_latitude, min_longitude, max_latitude, max_longitude)"
        )
    min_latitude, min_longitude, max_latitude, max_longitude = bbox
    for value in bbox:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("bbox values must be finite numbers")
    if not -90 <= min_latitude <= 90 or not -90 <= max_latitude <= 90:
        raise ValueError("bbox latitude must be between -90 and 90")
    if not -180 <= min_longitude <= 180 or not -180 <= max_longitude <= 180:
        raise ValueError("bbox longitude must be between -180 and 180")
    if min_latitude > max_latitude:
        raise ValueError("bbox min_latitude must be <= max_latitude")
    if min_longitude > max_longitude:
        raise ValueError("bbox min_longitude must be <= max_longitude")


def _require_timezone_aware(value: datetime | None, *, field: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field} must be timezone-aware")


class DetectionSource(ABC):
    async def fetch_hotspots(
        self,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        since: datetime | None = None,
    ) -> list[Hotspot]:
        _require_bbox_valid(bbox)
        _require_timezone_aware(since, field="since")
        return await self._fetch_hotspots(bbox=bbox, since=since)

    @abstractmethod
    async def _fetch_hotspots(
        self,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        since: datetime | None = None,
    ) -> list[Hotspot]:
        ...
