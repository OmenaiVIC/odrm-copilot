from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

DEFAULT_OPERATING_HOURS_PER_DAY: Final = 24.0
DEFAULT_OPERATING_DAYS_PER_YEAR: Final = 330.0
DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR: Final = 5.0
DEFAULT_CO2_UTILIZATION_FRACTION: Final = 0.0

ENGINEERING_DEFAULT_PROVENANCE: Final[Mapping[str, str]] = MappingProxyType(
    {
        "DEFAULT_OPERATING_HOURS_PER_DAY": (
            "Screening assumption: continuous steady-state operation; caller-overridable."
        ),
        "DEFAULT_OPERATING_DAYS_PER_YEAR": (
            "Screening assumption: conservative 90.4 % availability; caller-overridable."
        ),
        "DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR": (
            "Screening assumption: lumps maintenance, labour, overhead and consumables "
            "into one annual charge; caller-overridable."
        ),
        "DEFAULT_CO2_UTILIZATION_FRACTION": (
            "Conservative default: no carbon-credit value is invented unless the caller "
            "supplies a utilization fraction."
        ),
    }
)
