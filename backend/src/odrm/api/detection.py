from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from odrm.auth.dependencies import get_current_user
from odrm.detection.base import DetectionSource, Hotspot

router = APIRouter(dependencies=[Depends(get_current_user)])


def _parse_bbox(raw: str) -> tuple[float, float, float, float]:
    parts = raw.split(",")
    if len(parts) != 4:
        raise ValueError(
            "bbox must contain exactly four comma-separated values: "
            "min_latitude,min_longitude,max_latitude,max_longitude"
        )
    try:
        min_latitude, min_longitude, max_latitude, max_longitude = (
            float(part) for part in parts
        )
    except ValueError as exc:
        raise ValueError("bbox values must be numbers") from exc
    return (min_latitude, min_longitude, max_latitude, max_longitude)


@router.get("/detection/hotspots", response_model=list[Hotspot])
async def list_detection_hotspots(
    req: Request,
    bbox: Annotated[
        str | None,
        Query(
            description=(
                "Bounding box as "
                "min_latitude,min_longitude,max_latitude,max_longitude"
            )
        ),
    ] = None,
    since: Annotated[
        datetime | None,
        Query(description="Only return hotspots detected at or after this time."),
    ] = None,
) -> list[Hotspot]:
    source: DetectionSource = req.app.state.detection_source
    try:
        parsed_bbox = _parse_bbox(bbox) if bbox is not None else None
        return await source.fetch_hotspots(bbox=parsed_bbox, since=since)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_DETECTION_QUERY",
                "message": str(exc),
            },
        ) from exc
