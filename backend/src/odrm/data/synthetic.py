from __future__ import annotations

import uuid
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from odrm.data.schema import OPTIONAL, REQUIRED, SCHEMA_VERSION, validate_odrm_frame

FloatArray = NDArray[np.float64]

GENERATOR_VERSION = "1.0.0"
_RUN_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://odrm-copilot.local/synthetic/odrm/v1")

CATALYST_ACTIVITY: dict[str, float] = {
    "Ni/Al2O3": 1.0,
    "Ni-MgO": 0.98,
    "Rh": 1.2,
    "Pt": 1.12,
    "none": 0.15,
    "other": 0.85,
}
CATALYST_CARBON_RESISTANCE: dict[str, float] = {
    "Ni/Al2O3": 1.0,
    "Ni-MgO": 0.55,
    "Rh": 0.55,
    "Pt": 0.65,
    "none": 1.1,
    "other": 0.9,
}
CATALYST_WEIGHTS: dict[str, float] = {
    "Ni/Al2O3": 0.34,
    "Ni-MgO": 0.22,
    "Rh": 0.1,
    "Pt": 0.08,
    "none": 0.14,
    "other": 0.12,
}

_CH4_BUDGET = 0.95
_O2_BUDGET = 0.95


def _latin_hypercube(n: int, rng: np.random.Generator) -> FloatArray:
    strata = (np.arange(n, dtype=np.float64) + rng.random(n)) / float(n)
    return rng.permutation(strata).astype(np.float64)


def _clip(values: FloatArray, low: float, high: float) -> FloatArray:
    return np.clip(values, low, high)


def _carbon_risk(values: FloatArray) -> NDArray[np.str_]:
    return np.select(
        [values < 1.0, values < 5.0, values < 20.0],
        ["none", "low", "moderate"],
        default="high",
    ).astype(np.str_)


def _simulate(
    *,
    temperature_c: FloatArray,
    pressure_bar: FloatArray,
    ch4_o2_ratio: FloatArray,
    co2_ch4_ratio: FloatArray,
    h2o_ch4_ratio: FloatArray,
    ghsv_per_h: FloatArray,
    catalyst: NDArray[np.str_],
) -> dict[str, FloatArray | NDArray[np.str_]]:
    t = _clip((temperature_c - 500.0) / 500.0, 0.0, 1.0)
    thermal = np.exp(1.3 * (t - 0.5))
    pressure = (pressure_bar / 10.0) ** -0.3
    ghsv = (ghsv_per_h / 10000.0) ** -0.22
    co2_feed = _clip(co2_ch4_ratio, 0.0, 1.5)
    h2o_feed = _clip(h2o_ch4_ratio, 0.0, 1.5)
    o2_feed = 1.0 / ch4_o2_ratio

    activity = np.array([CATALYST_ACTIVITY[str(name)] for name in catalyst], dtype=np.float64)
    resistance = np.array(
        [CATALYST_CARBON_RESISTANCE[str(name)] for name in catalyst], dtype=np.float64
    )

    drm = 0.38 * activity * thermal * ghsv * pressure**0.75 * (0.25 + 0.85 * co2_feed)
    pom = 0.34 * activity * (0.6 + 0.4 * thermal) * ghsv * pressure**0.35 * (0.2 + 1.35 * o2_feed)
    steam_reforming = 0.14 * activity * thermal * ghsv * pressure**0.45 * (0.15 + 1.5 * h2o_feed)
    rwgs = 0.075 * activity * thermal * ghsv * (0.2 + 0.8 * co2_feed) * (0.3 + 0.7 * h2o_feed)
    cracking = (
        0.11
        * activity
        * (0.45 + 0.55 * t)
        * ghsv
        * pressure**0.55
        * (1.15 - 0.45 * co2_feed)
        * (1.0 - 0.25 * h2o_feed)
    )
    boudouard = (
        0.11
        * activity
        * (1.25 - 0.85 * t)
        * pressure**0.45
        * (1.0 - 0.45 * co2_feed)
        * (1.0 - 0.2 * h2o_feed)
    )
    excess_o2 = np.maximum(o2_feed - 0.46, 0.0)
    complete_oxidation = (
        30.0 * activity * (0.75 + 0.25 * thermal) * ghsv * pressure**0.1 * excess_o2**2
    )

    drm = np.minimum(drm, co2_feed * 0.85)
    rwgs = np.minimum(rwgs, np.maximum(co2_feed - drm, 0.0))
    pom = np.minimum(pom, 2.0 * o2_feed)
    steam_reforming = np.minimum(steam_reforming, h2o_feed)
    complete_oxidation = np.minimum(complete_oxidation, o2_feed / 2.0)

    total_ch4 = drm + pom + steam_reforming + cracking + complete_oxidation
    ch4_scale = np.where(total_ch4 > _CH4_BUDGET, _CH4_BUDGET / total_ch4, 1.0)
    drm *= ch4_scale
    pom *= ch4_scale
    steam_reforming *= ch4_scale
    cracking *= ch4_scale
    complete_oxidation *= ch4_scale

    o2_use = 0.5 * pom + 2.0 * complete_oxidation
    o2_cap = _O2_BUDGET * o2_feed
    o2_scale = np.where(o2_use > o2_cap, o2_cap / o2_use, 1.0)
    pom *= o2_scale
    complete_oxidation *= o2_scale

    co_pre = 2.0 * drm + pom + steam_reforming + rwgs - 2.0 * boudouard
    boudouard = np.minimum(boudouard, np.maximum(co_pre, 0.0) * 0.45)

    carbon_available = cracking + boudouard
    gas_fraction = _clip(0.05 + 0.55 * t + 0.35 * (co2_feed / 1.5) + 0.25 * h2o_feed, 0.0, 0.97)
    gasification = carbon_available * gas_fraction
    co2_available = co2_feed + complete_oxidation + boudouard - drm - rwgs
    gasification = np.minimum(gasification, np.maximum(co2_available, 0.0) * 0.9)
    gasification = np.minimum(gasification, carbon_available)

    ch4_out = 1.0 - drm - pom - steam_reforming - cracking - complete_oxidation
    co2_out = co2_feed + complete_oxidation + boudouard - drm - rwgs - gasification
    o2_out = o2_feed - 0.5 * pom - 2.0 * complete_oxidation
    h2_out = 2.0 * drm + 2.0 * pom + 3.0 * steam_reforming - rwgs + 2.0 * cracking
    co_out = 2.0 * drm + pom + steam_reforming + rwgs - 2.0 * boudouard + 2.0 * gasification
    h2o_out = h2o_feed - steam_reforming + rwgs + 2.0 * complete_oxidation
    carbon_out = cracking + boudouard - gasification

    carbon_deposition = 100.0 * (1.0 - np.exp(-2.2 * np.maximum(carbon_out, 0.0) * resistance))
    carbon_deposition = _clip(carbon_deposition, 0.0, 100.0)

    ch4_conversion = _clip(1.0 - ch4_out, 0.0, 1.0)
    co2_conversion = _clip((co2_feed - co2_out) / co2_feed, 0.0, 1.0)
    o2_conversion = _clip(1.0 - o2_out / o2_feed, 0.0, 1.0)
    h2_yield = _clip(h2_out, 0.0, 4.0)
    co_yield = _clip(co_out, 0.0, 4.0)

    c_feed = 1.0 + co2_feed
    h_feed = 4.0 + 2.0 * h2o_feed
    o_feed = 2.0 * co2_feed + h2o_feed + 2.0 * o2_feed
    c_out_atoms = ch4_out + co2_out + co_out + carbon_out
    h_out_atoms = 4.0 * ch4_out + 2.0 * h2o_out + 2.0 * h2_out
    o_out_atoms = 2.0 * co2_out + h2o_out + 2.0 * o2_out + co_out
    balance_error = (
        np.maximum.reduce(
            [
                np.abs(c_out_atoms - c_feed) / c_feed,
                np.abs(h_out_atoms - h_feed) / h_feed,
                np.abs(o_out_atoms - o_feed) / o_feed,
            ]
        )
        * 100.0
    )

    h2_co_ratio = h2_yield / co_yield

    return {
        "ch4_conversion": ch4_conversion,
        "co2_conversion": co2_conversion,
        "o2_conversion": o2_conversion,
        "h2_yield_mol_per_mol_ch4": h2_yield,
        "co_yield_mol_per_mol_ch4": co_yield,
        "h2_co_ratio": h2_co_ratio,
        "syngas_yield_mol_per_mol_ch4": h2_yield + co_yield,
        "ch4_slip_pct": (1.0 - ch4_conversion) * 100.0,
        "carbon_deposition_mg_per_gcat": carbon_deposition,
        "carbon_risk_class": _carbon_risk(carbon_deposition),
        "balance_error_pct": balance_error,
    }


def simulate_point(
    *,
    temperature_c: float,
    pressure_bar: float,
    ch4_o2_ratio: float,
    co2_ch4_ratio: float,
    h2o_ch4_ratio: float,
    ghsv_per_h: float,
    catalyst: str,
) -> dict[str, float | str]:
    """Evaluate the deterministic ODRM surrogate at one operating point."""
    result = _simulate(
        temperature_c=np.array([temperature_c], dtype=np.float64),
        pressure_bar=np.array([pressure_bar], dtype=np.float64),
        ch4_o2_ratio=np.array([ch4_o2_ratio], dtype=np.float64),
        co2_ch4_ratio=np.array([co2_ch4_ratio], dtype=np.float64),
        h2o_ch4_ratio=np.array([h2o_ch4_ratio], dtype=np.float64),
        ghsv_per_h=np.array([ghsv_per_h], dtype=np.float64),
        catalyst=np.array([catalyst], dtype=np.str_),
    )
    output: dict[str, float | str] = {}
    for name, values in result.items():
        if name == "carbon_risk_class":
            output[name] = str(values[0])
        else:
            output[name] = float(values[0])
    return output


def generate_odrm_frame(
    *,
    n: int = 10000,
    seed: int = 7,
    created_at_base: datetime | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Generate a deterministic, validated v1 synthetic ODRM frame."""
    if n <= 0:
        raise ValueError("n must be greater than zero")

    base = pd.Timestamp(created_at_base or datetime(2026, 1, 1, tzinfo=UTC))
    if base.tzinfo is None:
        raise ValueError("created_at_base must be timezone-aware")
    base = base.tz_convert("UTC")

    rng = np.random.Generator(np.random.PCG64(seed))
    u = np.column_stack([_latin_hypercube(n, rng) for _ in range(6)])

    temperature_c = 500.0 + 500.0 * u[:, 0]
    pressure_bar = 10.0 ** (np.log10(1.0) + u[:, 1] * (np.log10(30.0) - np.log10(1.0)))
    ch4_o2_ratio = 1.4 + (2.5 - 1.4) * u[:, 2]
    co2_ch4_ratio = 0.05 + (1.5 - 0.05) * u[:, 3]
    h2o_ch4_ratio = 1.0 * u[:, 4]
    ghsv_per_h = 10.0 ** (np.log10(1000.0) + u[:, 5] * (np.log10(100000.0) - np.log10(1000.0)))

    catalysts = np.array(list(CATALYST_WEIGHTS), dtype=np.str_)
    probabilities = np.array(list(CATALYST_WEIGHTS.values()), dtype=np.float64)
    catalyst = rng.choice(catalysts, size=n, p=probabilities).astype(np.str_)

    simulated = _simulate(
        temperature_c=temperature_c,
        pressure_bar=pressure_bar,
        ch4_o2_ratio=ch4_o2_ratio,
        co2_ch4_ratio=co2_ch4_ratio,
        h2o_ch4_ratio=h2o_ch4_ratio,
        ghsv_per_h=ghsv_per_h,
        catalyst=catalyst,
    )

    indices = np.arange(n, dtype=np.int64)
    run_ids = [
        str(
            uuid.uuid5(
                _RUN_NAMESPACE,
                f"{GENERATOR_VERSION}|{seed}|{index}",
            )
        )
        for index in indices
    ]
    created_at = pd.date_range(base, periods=n, freq="s")

    loading = rng.uniform(2.0, 15.0, size=n)
    loading = np.where(catalyst == "none", np.nan, loading)
    dilution = rng.uniform(0.0, 30.0, size=n)
    dilution = np.where(rng.random(n) < 0.4, np.nan, dilution)
    energy = 500.0 + 3.0 * (temperature_c - 500.0) + ghsv_per_h / 100.0

    columns: dict[str, object] = {
        "run_id": run_ids,
        "created_at": created_at,
        "source": np.full(n, "synthetic", dtype=object),
        "schema_version": np.full(n, SCHEMA_VERSION, dtype=object),
        "catalyst": catalyst,
        "temperature_c": temperature_c,
        "pressure_bar": pressure_bar,
        "ch4_o2_ratio": ch4_o2_ratio,
        "co2_ch4_ratio": co2_ch4_ratio,
        "h2o_ch4_ratio": h2o_ch4_ratio,
        "ghsv_per_h": ghsv_per_h,
        **{name: values for name, values in simulated.items() if name != "carbon_risk_class"},
        "carbon_risk_class": simulated["carbon_risk_class"],
        "quality_flag": np.full(n, "valid", dtype=object),
        "reactor_id": [f"SYN-R-{1 + index % 12:03d}" for index in indices],
        "catalyst_loading_wt_pct": loading,
        "n2_dilution_mol_pct": dilution,
        "contact_time_ms": np.full(n, np.nan, dtype=np.float64),
        "energy_input_kw": energy,
        "notes": np.full(n, None, dtype=object),
    }

    frame = pd.DataFrame(columns)
    expected = list(REQUIRED) + list(OPTIONAL)
    return validate_odrm_frame(frame.loc[:, expected])
