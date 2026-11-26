"""Integration tests for the detection hotspots API route."""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.integration

HOTSPOTS_PATH = "/api/v1/detection/hotspots"
EXPECTED_IDS = [f"mock-nogiet-{index:03d}" for index in range(1, 7)]
EXPECTED_FIELDS = {
    "id",
    "latitude",
    "longitude",
    "intensity_ppb",
    "detected_at",
    "source",
}


def test_detection_endpoint_requires_auth(anonymous_client: Any) -> None:
    response = anonymous_client.get(HOTSPOTS_PATH)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_detection_endpoint_returns_all_fixtures(client: Any) -> None:
    response = client.get(HOTSPOTS_PATH)
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert [hotspot["id"] for hotspot in payload] == EXPECTED_IDS
    assert all(set(hotspot) == EXPECTED_FIELDS for hotspot in payload)
    assert all(hotspot["source"] == "mock_nogiet" for hotspot in payload)


def test_detection_endpoint_filters_by_bbox(client: Any) -> None:
    response = client.get(
        HOTSPOTS_PATH,
        params={"bbox": "4.80,7.00,4.83,7.06"},
    )
    assert response.status_code == 200
    assert [hotspot["id"] for hotspot in response.json()] == [
        "mock-nogiet-001",
        "mock-nogiet-005",
    ]


def test_detection_endpoint_filters_by_since(client: Any) -> None:
    response = client.get(
        HOTSPOTS_PATH,
        params={"since": "2026-02-01T00:00:00Z"},
    )
    assert response.status_code == 200
    assert [hotspot["id"] for hotspot in response.json()] == [
        "mock-nogiet-004",
        "mock-nogiet-005",
        "mock-nogiet-006",
    ]


@pytest.mark.parametrize(
    "bbox",
    [
        "4.80,7.00,4.83",
        "91.0,7.00,92.0,7.06",
        "4.80,7.00,nan,7.06",
    ],
)
def test_detection_endpoint_rejects_invalid_bbox(
    client: Any,
    bbox: str,
) -> None:
    response = client.get(HOTSPOTS_PATH, params={"bbox": bbox})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_DETECTION_QUERY"


def test_detection_endpoint_rejects_naive_since(client: Any) -> None:
    response = client.get(
        HOTSPOTS_PATH,
        params={"since": "2026-02-01T00:00:00"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_DETECTION_QUERY"
