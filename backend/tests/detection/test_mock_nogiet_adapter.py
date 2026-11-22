"""Unit tests for the demonstration NOGIET-style detection adapter."""

from __future__ import annotations

import inspect
import math
from datetime import UTC, datetime, timedelta

import pytest

import odrm.detection.mock_nogiet as mock_nogiet_module
from odrm.detection import DetectionSource, Hotspot
from odrm.detection.mock_nogiet import MockNogietAdapter

pytestmark = pytest.mark.unit

BBOX_PH_WOJI = (4.80, 7.02, 4.82, 7.06)
BBOX_BOUNDARY = (4.8156, 7.0498, 4.8156, 7.0498)
BBOX_COMBINED = (4.70, 7.10, 4.90, 7.20)
SINCE_MID: datetime = datetime(2026, 1, 15, tzinfo=UTC)
SINCE_EQUAL_004: datetime = datetime(2026, 2, 2, 18, 0, tzinfo=UTC)
SINCE_COMBINED: datetime = datetime(2026, 2, 1, tzinfo=UTC)
EMPTY_BBOX = (0.0, 0.0, 1.0, 1.0)
FUTURE_SINCE: datetime = datetime(2027, 1, 1, tzinfo=UTC)


def test_adapter_is_detection_source_subclass() -> None:
    assert issubclass(MockNogietAdapter, DetectionSource)


def test_adapter_does_not_override_fetch_hotspots() -> None:
    assert "fetch_hotspots" not in MockNogietAdapter.__dict__
    assert MockNogietAdapter.fetch_hotspots is DetectionSource.fetch_hotspots
    assert "_fetch_hotspots" in MockNogietAdapter.__dict__
    assert inspect.iscoroutinefunction(MockNogietAdapter._fetch_hotspots)


async def test_default_fetch_returns_at_least_five_hotspots() -> None:
    result = await MockNogietAdapter().fetch_hotspots()
    assert isinstance(result, list)
    assert len(result) >= 5
    assert all(isinstance(hotspot, Hotspot) for hotspot in result)


async def test_every_fixture_has_mock_nogiet_source() -> None:
    result = await MockNogietAdapter().fetch_hotspots()
    assert result
    assert all(hotspot.source == "mock_nogiet" for hotspot in result)


async def test_fixtures_use_niger_delta_coordinates() -> None:
    result = await MockNogietAdapter().fetch_hotspots()
    assert result
    assert all(4.0 <= hotspot.latitude <= 5.5 for hotspot in result)
    assert all(6.5 <= hotspot.longitude <= 7.5 for hotspot in result)
    assert any(
        abs(hotspot.latitude - 4.8) <= 0.1
        and abs(hotspot.longitude - 7.0) <= 0.1
        for hotspot in result
    )


async def test_fixtures_have_mixed_timestamps_and_intensities() -> None:
    result = await MockNogietAdapter().fetch_hotspots()
    assert len({hotspot.detected_at for hotspot in result}) >= 2
    assert len({hotspot.intensity_ppb for hotspot in result}) >= 2
    assert all(math.isfinite(hotspot.intensity_ppb) for hotspot in result)
    assert all(hotspot.intensity_ppb >= 0 for hotspot in result)
    assert all(hotspot.detected_at.tzinfo is not None for hotspot in result)
    assert all(
        hotspot.detected_at.utcoffset() == timedelta(0) for hotspot in result
    )


async def test_fixtures_are_schema_conformant_with_no_nulls() -> None:
    result = await MockNogietAdapter().fetch_hotspots()
    assert result
    expected_fields = {
        "id",
        "latitude",
        "longitude",
        "intensity_ppb",
        "detected_at",
        "source",
    }
    assert len({hotspot.id for hotspot in result}) == len(result)
    for hotspot in result:
        assert isinstance(hotspot, Hotspot)
        payload = hotspot.model_dump()
        assert set(payload) == expected_fields
        assert all(value is not None for value in payload.values())
        assert Hotspot.model_validate(payload) == hotspot


async def test_bbox_filter_returns_only_hotspots_inside_box() -> None:
    result = await MockNogietAdapter().fetch_hotspots(bbox=BBOX_PH_WOJI)
    assert [hotspot.id for hotspot in result] == [
        "mock-nogiet-001",
        "mock-nogiet-005",
    ]


async def test_bbox_filter_includes_exact_boundary_hotspots() -> None:
    result = await MockNogietAdapter().fetch_hotspots(bbox=BBOX_BOUNDARY)
    assert [hotspot.id for hotspot in result] == ["mock-nogiet-001"]


async def test_since_filter_returns_only_hotspots_at_or_after_since() -> None:
    result = await MockNogietAdapter().fetch_hotspots(since=SINCE_MID)
    assert [hotspot.id for hotspot in result] == [
        "mock-nogiet-003",
        "mock-nogiet-004",
        "mock-nogiet-005",
        "mock-nogiet-006",
    ]


async def test_since_filter_includes_exact_boundary_timestamp() -> None:
    result = await MockNogietAdapter().fetch_hotspots(since=SINCE_EQUAL_004)
    assert [hotspot.id for hotspot in result] == [
        "mock-nogiet-004",
        "mock-nogiet-005",
        "mock-nogiet-006",
    ]


async def test_bbox_and_since_filters_combine() -> None:
    result = await MockNogietAdapter().fetch_hotspots(
        bbox=BBOX_COMBINED,
        since=SINCE_COMBINED,
    )
    assert [hotspot.id for hotspot in result] == ["mock-nogiet-004"]


async def test_filters_can_return_empty_list() -> None:
    adapter = MockNogietAdapter()
    assert await adapter.fetch_hotspots(bbox=EMPTY_BBOX) == []
    assert await adapter.fetch_hotspots(since=FUTURE_SINCE) == []
    assert await adapter.fetch_hotspots(bbox=EMPTY_BBOX, since=FUTURE_SINCE) == []


@pytest.mark.parametrize(
    "bbox",
    [
        (4.0, 7.0, 5.0),
        (4.0, 7.0, 5.0, 8.0, 9.0),
        (5.0, 7.0, 4.0, 8.0),
        (4.0, 8.0, 5.0, 7.0),
        (-91.0, 7.0, 5.0, 8.0),
        (4.0, -181.0, 5.0, 8.0),
        (4.0, 7.0, 91.0, 8.0),
        (4.0, 7.0, 5.0, 181.0),
        (4.0, 7.0, math.inf, 8.0),
    ],
)
async def test_invalid_bbox_is_rejected_by_inherited_validation(
    bbox: tuple[float, ...],
) -> None:
    with pytest.raises(ValueError):
        await MockNogietAdapter().fetch_hotspots(bbox=bbox)  # type: ignore[arg-type]


async def test_naive_since_is_rejected_by_inherited_validation() -> None:
    with pytest.raises(ValueError, match=r"^since must be timezone-aware$"):
        await MockNogietAdapter().fetch_hotspots(since=datetime(2026, 1, 1))


def test_module_docstring_contains_required_disclaimers() -> None:
    docstring = mock_nogiet_module.__doc__ or ""
    lowered = docstring.lower()
    required_phrases = [
        "demonstration adapter",
        "does not integrate with nogiet",
        "nuprc",
        "nmdpra",
        "sdn",
        "at no cost",
        "valoris has no role",
    ]
    assert all(phrase in lowered for phrase in required_phrases)


async def test_repeated_calls_are_deterministic_and_return_new_lists() -> None:
    adapter = MockNogietAdapter()
    first = await adapter.fetch_hotspots()
    second = await adapter.fetch_hotspots()
    assert first == second
    assert [hotspot.id for hotspot in first] == [hotspot.id for hotspot in second]
    assert first is not second


async def test_filtered_results_preserve_fixture_order() -> None:
    adapter = MockNogietAdapter()
    spatial_ids = [
        hotspot.id
        for hotspot in await adapter.fetch_hotspots(bbox=BBOX_COMBINED)
    ]
    temporal_ids = [
        hotspot.id
        for hotspot in await adapter.fetch_hotspots(since=SINCE_MID)
    ]
    combined_ids = [
        hotspot.id
        for hotspot in await adapter.fetch_hotspots(
            bbox=BBOX_COMBINED,
            since=SINCE_COMBINED,
        )
    ]
    assert spatial_ids == ["mock-nogiet-003", "mock-nogiet-004"]
    assert temporal_ids == [
        "mock-nogiet-003",
        "mock-nogiet-004",
        "mock-nogiet-005",
        "mock-nogiet-006",
    ]
    assert combined_ids == ["mock-nogiet-004"]
