from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from odrm.detection import DetectionSource, Hotspot

pytestmark = pytest.mark.unit


def valid_hotspot_payload() -> dict[str, object]:
    return {
        "id": "hotspot-1",
        "latitude": 4.8156,
        "longitude": 7.0498,
        "intensity_ppb": 1850.0,
        "detected_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "source": "test-source",
    }


class StubSource(DetectionSource):
    def __init__(self) -> None:
        self.received_bbox: tuple[float, float, float, float] | None = None
        self.received_since: datetime | None = None

    async def _fetch_hotspots(
        self,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        since: datetime | None = None,
    ) -> list[Hotspot]:
        self.received_bbox = bbox
        self.received_since = since
        return [Hotspot.model_validate(valid_hotspot_payload())]


def test_hotspot_accepts_valid_six_field_payload() -> None:
    hotspot = Hotspot.model_validate(valid_hotspot_payload())
    assert hotspot.id == "hotspot-1"
    assert hotspot.latitude == 4.8156
    assert hotspot.longitude == 7.0498
    assert hotspot.intensity_ppb == 1850.0
    assert hotspot.detected_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert hotspot.source == "test-source"


def test_hotspot_declares_exactly_six_fields() -> None:
    assert set(Hotspot.model_fields) == {
        "id",
        "latitude",
        "longitude",
        "intensity_ppb",
        "detected_at",
        "source",
    }


def test_hotspot_rejects_extra_confidence_field() -> None:
    payload = valid_hotspot_payload()
    payload["confidence"] = 0.9
    with pytest.raises(ValidationError):
        Hotspot.model_validate(payload)


@pytest.mark.parametrize("latitude", [-90.01, 90.01])
def test_hotspot_rejects_out_of_range_latitude(latitude: float) -> None:
    payload = valid_hotspot_payload()
    payload["latitude"] = latitude
    with pytest.raises(ValidationError):
        Hotspot.model_validate(payload)


@pytest.mark.parametrize("longitude", [-180.01, 180.01])
def test_hotspot_rejects_out_of_range_longitude(longitude: float) -> None:
    payload = valid_hotspot_payload()
    payload["longitude"] = longitude
    with pytest.raises(ValidationError):
        Hotspot.model_validate(payload)


def test_hotspot_rejects_negative_intensity() -> None:
    payload = valid_hotspot_payload()
    payload["intensity_ppb"] = -0.01
    with pytest.raises(ValidationError):
        Hotspot.model_validate(payload)


@pytest.mark.parametrize("intensity", [float("inf"), float("-inf"), float("nan")])
def test_hotspot_rejects_non_finite_intensity(intensity: float) -> None:
    payload = valid_hotspot_payload()
    payload["intensity_ppb"] = intensity
    with pytest.raises(ValidationError):
        Hotspot.model_validate(payload)


def test_detection_source_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        DetectionSource()


def test_fetch_hotspots_is_async_and_exposes_filters() -> None:
    assert inspect.iscoroutinefunction(DetectionSource.fetch_hotspots)
    parameters = inspect.signature(DetectionSource.fetch_hotspots).parameters
    assert parameters["bbox"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["since"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["bbox"].default is None
    assert parameters["since"].default is None


async def test_concrete_source_can_be_awaited() -> None:
    result = await StubSource().fetch_hotspots()
    assert len(result) == 1
    assert isinstance(result[0], Hotspot)


async def test_concrete_source_receives_filters() -> None:
    source = StubSource()
    bbox = (4.0, 7.0, 5.0, 8.0)
    since = datetime(2026, 1, 1, tzinfo=UTC)
    await source.fetch_hotspots(bbox=bbox, since=since)
    assert source.received_bbox == bbox
    assert source.received_since == since


async def test_fetch_hotspots_accepts_valid_bbox() -> None:
    result = await StubSource().fetch_hotspots(bbox=(-90.0, -180.0, 90.0, 180.0))
    assert len(result) == 1


@pytest.mark.parametrize("bbox", [(1.0, 2.0, 3.0), (1.0, 2.0, 3.0, 4.0, 5.0)])
async def test_fetch_hotspots_rejects_bbox_with_wrong_length(
    bbox: tuple[float, ...],
) -> None:
    with pytest.raises(ValueError, match="bbox must contain exactly four values"):
        await StubSource().fetch_hotspots(bbox=bbox)


@pytest.mark.parametrize(
    "bbox",
    [
        (-91.0, 0.0, 0.0, 1.0),
        (0.0, 0.0, 91.0, 1.0),
    ],
)
async def test_fetch_hotspots_rejects_out_of_range_bbox_latitude(
    bbox: tuple[float, float, float, float],
) -> None:
    with pytest.raises(ValueError, match="bbox latitude must be between -90 and 90"):
        await StubSource().fetch_hotspots(bbox=bbox)


@pytest.mark.parametrize(
    "bbox",
    [
        (0.0, -181.0, 1.0, 1.0),
        (0.0, 0.0, 1.0, 181.0),
    ],
)
async def test_fetch_hotspots_rejects_out_of_range_bbox_longitude(
    bbox: tuple[float, float, float, float],
) -> None:
    with pytest.raises(ValueError, match="bbox longitude must be between -180 and 180"):
        await StubSource().fetch_hotspots(bbox=bbox)


@pytest.mark.parametrize(
    ("bbox", "message"),
    [
        ((10.0, 0.0, 5.0, 1.0), "bbox min_latitude must be <= max_latitude"),
        ((0.0, 10.0, 1.0, 5.0), "bbox min_longitude must be <= max_longitude"),
    ],
)
async def test_fetch_hotspots_rejects_inverted_bbox_bounds(
    bbox: tuple[float, float, float, float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        await StubSource().fetch_hotspots(bbox=bbox)


@pytest.mark.parametrize(
    "bbox",
    [
        (0.0, 0.0, float("inf"), 1.0),
        (0.0, 0.0, float("-inf"), 1.0),
        (0.0, 0.0, float("nan"), 1.0),
    ],
)
async def test_fetch_hotspots_rejects_non_finite_bbox_values(
    bbox: tuple[float, float, float, float],
) -> None:
    with pytest.raises(ValueError, match="bbox values must be finite numbers"):
        await StubSource().fetch_hotspots(bbox=bbox)


async def test_fetch_hotspots_rejects_bool_in_bbox() -> None:
    with pytest.raises(ValueError, match="bbox values must be finite numbers"):
        await StubSource().fetch_hotspots(
            bbox=(True, 0.0, 1.0, 1.0)  # type: ignore[arg-type]
        )


async def test_fetch_hotspots_rejects_naive_since() -> None:
    with pytest.raises(ValueError) as exc_info:
        await StubSource().fetch_hotspots(since=datetime(2026, 1, 1))
    assert str(exc_info.value) == "since must be timezone-aware"


async def test_fetch_hotspots_accepts_aware_since() -> None:
    result = await StubSource().fetch_hotspots(
        since=datetime(2026, 1, 1, tzinfo=UTC)
    )
    assert len(result) == 1
