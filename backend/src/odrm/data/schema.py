from __future__ import annotations

import math

REQUIRED: dict[str, str] = {
    "run_id": "string",
    "created_at": "string",
    "source": "string",
    "schema_version": "const",
    "catalyst": "string",
    "temperature_c": "number",
    "pressure_bar": "number",
    "ch4_o2_ratio": "number",
    "co2_ch4_ratio": "number",
    "h2o_ch4_ratio": "number",
    "ghsv_per_h": "number",
    "ch4_conversion": "number",
    "co2_conversion": "number",
    "o2_conversion": "number",
    "h2_yield_mol_per_mol_ch4": "number",
    "co_yield_mol_per_mol_ch4": "number",
    "h2_co_ratio": "number",
    "syngas_yield_mol_per_mol_ch4": "number",
    "ch4_slip_pct": "number",
    "carbon_deposition_mg_per_gcat": "number",
    "carbon_risk_class": "string",
    "balance_error_pct": "number",
    "quality_flag": "string",
}

OPTIONAL: dict[str, str] = {
    "reactor_id": "string",
    "catalyst_loading_wt_pct": "number",
    "n2_dilution_mol_pct": "number",
    "contact_time_ms": "number",
    "energy_input_kw": "number",
    "notes": "string",
}

DERIVED_COLUMNS: tuple[str, ...] = (
    "h2_co_ratio",
    "syngas_yield_mol_per_mol_ch4",
    "ch4_slip_pct",
    "carbon_risk_class",
)

ENUMS: dict[str, tuple[str, ...]] = {
    "source": ("experimental", "aspen_hysys", "comsol", "synthetic", "plant"),
    "catalyst": ("Ni/Al2O3", "Ni-MgO", "Rh", "Pt", "none", "other"),
    "carbon_risk_class": ("none", "low", "moderate", "high"),
    "quality_flag": ("valid", "suspect", "rejected"),
}

BOUNDS: dict[str, tuple[float, float]] = {
    "catalyst_loading_wt_pct": (0.0, 20.0),
    "temperature_c": (500.0, 1000.0),
    "pressure_bar": (1.0, 30.0),
    "ch4_o2_ratio": (1.4, 2.5),
    "co2_ch4_ratio": (0.0, 1.5),
    "h2o_ch4_ratio": (0.0, 1.5),
    "ghsv_per_h": (1000.0, 100000.0),
    "n2_dilution_mol_pct": (0.0, 50.0),
    "contact_time_ms": (0.0, math.inf),
    "ch4_conversion": (0.0, 1.0),
    "co2_conversion": (0.0, 1.0),
    "o2_conversion": (0.0, 1.0),
    "h2_yield_mol_per_mol_ch4": (0.0, 4.0),
    "co_yield_mol_per_mol_ch4": (0.0, 4.0),
    "h2_co_ratio": (0.0, math.inf),
    "syngas_yield_mol_per_mol_ch4": (0.0, 8.0),
    "ch4_slip_pct": (0.0, 100.0),
    "carbon_deposition_mg_per_gcat": (0.0, 100.0),
    "energy_input_kw": (0.0, 100000.0),
    "balance_error_pct": (-2.0, 2.0),
}

EXCLUSIVE_MINIMUMS: dict[str, float] = {
    "contact_time_ms": 0.0,
}

RISK_THRESHOLDS: dict[str, tuple[float, float | None]] = {
    "none": (0.0, 1.0),
    "low": (1.0, 5.0),
    "moderate": (5.0, 20.0),
    "high": (20.0, None),
}

SCHEMA_VERSION = "v1"
BALANCE_ERROR_TOLERANCE_PCT = 2.0


class SchemaError(ValueError):
    """Raised when an ODRM frame violates the v1 contract."""


class BoundsError(SchemaError):
    """Raised when a numeric value falls outside its physics bounds."""


class BalanceError(SchemaError):
    """Raised when the reported elemental balance error is unphysical."""
