"""Demonstration NOGIET-style detection adapter with synthetic fixtures.

This is a demonstration adapter. It does not integrate with NOGIET and performs
no network, filesystem, or database I/O. NOGIET is a public methane tracking
platform built by the Stakeholder Democracy Network (SDN) with Global Methane
Hub support and transferred to NUPRC and NMDPRA at no cost. Valoris has no role
in NOGIET's development or operation.

The fixture hotspots are synthetic, schema-conformant demonstration data. They
are not real observations and must not be represented as regulatory or
scientific measurements.
"""

from __future__ import annotations

from datetime import UTC, datetime

from odrm.detection.base import DetectionSource, Hotspot

_SOURCE = "mock_nogiet"

_FIXTURES: tuple[Hotspot, ...] = (
    Hotspot(
        id="mock-nogiet-001",
        latitude=4.8156,
        longitude=7.0498,
        intensity_ppb=2450.0,
        detected_at=datetime(2026, 1, 5, 9, 30, tzinfo=UTC),
        source=_SOURCE,
    ),
    Hotspot(
        id="mock-nogiet-002",
        latitude=4.7400,
        longitude=7.0833,
        intensity_ppb=3120.0,
        detected_at=datetime(2026, 1, 12, 14, 15, tzinfo=UTC),
        source=_SOURCE,
    ),
    Hotspot(
        id="mock-nogiet-003",
        latitude=4.7833,
        longitude=7.1167,
        intensity_ppb=1920.0,
        detected_at=datetime(2026, 1, 20, 6, 45, tzinfo=UTC),
        source=_SOURCE,
    ),
    Hotspot(
        id="mock-nogiet-004",
        latitude=4.7167,
        longitude=7.1500,
        intensity_ppb=4600.0,
        detected_at=datetime(2026, 2, 2, 18, 0, tzinfo=UTC),
        source=_SOURCE,
    ),
    Hotspot(
        id="mock-nogiet-005",
        latitude=4.8167,
        longitude=7.0333,
        intensity_ppb=2280.0,
        detected_at=datetime(2026, 2, 10, 11, 20, tzinfo=UTC),
        source=_SOURCE,
    ),
    Hotspot(
        id="mock-nogiet-006",
        latitude=4.8833,
        longitude=6.9000,
        intensity_ppb=5210.0,
        detected_at=datetime(2026, 2, 18, 7, 5, tzinfo=UTC),
        source=_SOURCE,
    ),
)


class MockNogietAdapter(DetectionSource):
    """Return deterministic synthetic Niger Delta hotspot fixtures."""

    _fixtures: tuple[Hotspot, ...] = _FIXTURES

    async def _fetch_hotspots(
        self,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        since: datetime | None = None,
    ) -> list[Hotspot]:
        hotspots = self._fixtures
        if bbox is not None:
            min_latitude, min_longitude, max_latitude, max_longitude = bbox
            hotspots = tuple(
                hotspot
                for hotspot in hotspots
                if min_latitude <= hotspot.latitude <= max_latitude
                and min_longitude <= hotspot.longitude <= max_longitude
            )
        if since is not None:
            hotspots = tuple(
                hotspot for hotspot in hotspots if hotspot.detected_at >= since
            )
        return list(hotspots)
