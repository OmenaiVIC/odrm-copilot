from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from odrm.data.schema import BOUNDS, OPTIONAL, REQUIRED, validate_odrm_frame
from odrm.data.synthetic import GENERATOR_VERSION, generate_odrm_frame, simulate_point

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _point(**overrides: float | str) -> dict[str, float | str]:
    defaults: dict[str, float | str] = {
        "temperature_c": 750.0,
        "pressure_bar": 10.0,
        "ch4_o2_ratio": 2.0,
        "co2_ch4_ratio": 0.75,
        "h2o_ch4_ratio": 0.25,
        "ghsv_per_h": 10000.0,
        "catalyst": "Ni/Al2O3",
    }
    defaults.update(overrides)
    return simulate_point(**defaults)  # type: ignore[arg-type]


def test_generator_is_deterministic_for_seed() -> None:
    first = generate_odrm_frame(n=128, seed=7, created_at_base=BASE)
    second = generate_odrm_frame(n=128, seed=7, created_at_base=BASE)

    pd.testing.assert_frame_equal(first, second)


def test_different_seed_changes_stochastic_columns() -> None:
    first = generate_odrm_frame(n=128, seed=7, created_at_base=BASE)
    second = generate_odrm_frame(n=128, seed=8, created_at_base=BASE)

    assert not first["run_id"].equals(second["run_id"])
    assert not first["temperature_c"].equals(second["temperature_c"])


def test_generator_returns_complete_valid_contract() -> None:
    frame = generate_odrm_frame(n=256, seed=7, created_at_base=BASE)

    assert len(frame) == 256
    assert set(frame.columns) == set(REQUIRED) | set(OPTIONAL)
    assert frame["run_id"].is_unique
    assert (frame["source"].astype(str) == "synthetic").all()
    assert (frame["schema_version"].astype(str) == "v1").all()
    assert (frame["quality_flag"].astype(str) == "valid").all()
    assert frame["notes"].isna().all()
    assert frame["contact_time_ms"].isna().all()

    validated = validate_odrm_frame(frame)
    pd.testing.assert_frame_equal(frame, validated)


def test_generator_uses_deterministic_timestamps_and_uuids() -> None:
    frame = generate_odrm_frame(n=8, seed=7, created_at_base=BASE)

    expected = pd.date_range(BASE, periods=8, freq="s")
    assert frame["created_at"].tolist() == expected.tolist()
    assert frame["run_id"].iloc[0] == frame["run_id"].iloc[0]
    assert frame["run_id"].str.len().eq(36).all()


def test_generator_covers_envelope_and_risk_classes() -> None:
    frame = generate_odrm_frame(n=10000, seed=7, created_at_base=BASE)

    assert frame["temperature_c"].min() < 501.0
    assert frame["temperature_c"].max() > 999.0
    assert frame["pressure_bar"].min() < 1.1
    assert frame["pressure_bar"].max() > 28.0
    assert frame["ghsv_per_h"].min() < 1100.0
    assert frame["ghsv_per_h"].max() > 95000.0
    assert set(frame["carbon_risk_class"].astype(str)) == {
        "none",
        "low",
        "moderate",
        "high",
    }


def test_generator_leaves_global_rng_untouched() -> None:
    state_before = np.random.get_state()
    generate_odrm_frame(n=64, seed=7, created_at_base=BASE)
    state_after = np.random.get_state()

    assert state_before[0] == state_after[0]
    assert np.array_equal(state_before[1], state_after[1])
    assert state_before[2:] == state_after[2:]


def test_generated_rows_balance_and_bounds() -> None:
    frame = generate_odrm_frame(n=1000, seed=7, created_at_base=BASE)

    assert (frame["balance_error_pct"].abs() < 1e-6).all()
    for name, (low, high) in BOUNDS.items():
        values = frame[name].dropna()
        assert (values >= low).all(), name
        if np.isfinite(high):
            assert (values <= high).all(), name


def test_temperature_trends() -> None:
    cold = _point(temperature_c=600.0)
    hot = _point(temperature_c=950.0)

    assert hot["ch4_conversion"] > cold["ch4_conversion"]
    assert hot["syngas_yield_mol_per_mol_ch4"] > cold["syngas_yield_mol_per_mol_ch4"]
    assert hot["carbon_deposition_mg_per_gcat"] < cold["carbon_deposition_mg_per_gcat"]


def test_pressure_suppresses_conversion() -> None:
    low = _point(pressure_bar=2.0)
    high = _point(pressure_bar=25.0)

    assert low["ch4_conversion"] > high["ch4_conversion"]
    assert low["syngas_yield_mol_per_mol_ch4"] > high["syngas_yield_mol_per_mol_ch4"]


def test_excess_co2_promotes_conversion_and_lowers_h2_co() -> None:
    low = _point(co2_ch4_ratio=0.1)
    high = _point(co2_ch4_ratio=1.4)

    assert high["ch4_conversion"] > low["ch4_conversion"]
    assert high["h2_co_ratio"] < low["h2_co_ratio"]
    assert high["carbon_deposition_mg_per_gcat"] < low["carbon_deposition_mg_per_gcat"]


def test_steam_promotes_hydrogen() -> None:
    dry = _point(h2o_ch4_ratio=0.0)
    wet = _point(h2o_ch4_ratio=1.0)

    assert wet["h2_yield_mol_per_mol_ch4"] > dry["h2_yield_mol_per_mol_ch4"]
    assert wet["h2_co_ratio"] > dry["h2_co_ratio"]
    assert wet["syngas_yield_mol_per_mol_ch4"] > dry["syngas_yield_mol_per_mol_ch4"]


def test_oxygen_sweep_has_interior_syngas_optimum() -> None:
    ratios = np.linspace(1.4, 2.5, 23)
    syngas = np.array(
        [_point(ch4_o2_ratio=float(ratio))["syngas_yield_mol_per_mol_ch4"] for ratio in ratios]
    )

    peak = int(np.argmax(syngas))
    assert 0 < peak < len(ratios) - 1
    assert 1.7 < ratios[peak] < 2.3
    assert syngas[0] < syngas[peak]
    assert syngas[-1] < syngas[peak]


def test_higher_ghsv_reduces_approach_to_equilibrium() -> None:
    low = _point(ghsv_per_h=2000.0)
    high = _point(ghsv_per_h=80000.0)

    assert low["ch4_conversion"] > high["ch4_conversion"]
    assert low["syngas_yield_mol_per_mol_ch4"] > high["syngas_yield_mol_per_mol_ch4"]


def test_catalyst_activity_ordering() -> None:
    ni = _point(catalyst="Ni/Al2O3")
    rh = _point(catalyst="Rh")
    pt = _point(catalyst="Pt")
    inert = _point(catalyst="none")

    assert rh["ch4_conversion"] > ni["ch4_conversion"]
    assert pt["ch4_conversion"] > ni["ch4_conversion"]
    assert inert["ch4_conversion"] < ni["ch4_conversion"]
    assert inert["ch4_conversion"] < rh["ch4_conversion"]


def test_ni_mgo_is_more_carbon_resistant_than_ni_al2o3() -> None:
    coking = {
        "temperature_c": 900.0,
        "pressure_bar": 25.0,
        "ch4_o2_ratio": 2.4,
        "co2_ch4_ratio": 0.05,
        "h2o_ch4_ratio": 0.0,
        "ghsv_per_h": 3000.0,
    }
    ni = _point(catalyst="Ni/Al2O3", **coking)
    mgo = _point(catalyst="Ni-MgO", **coking)

    assert mgo["carbon_deposition_mg_per_gcat"] < ni["carbon_deposition_mg_per_gcat"]


def test_simulated_points_balance_across_envelope() -> None:
    for temperature in (500.0, 650.0, 750.0, 850.0, 1000.0):
        for pressure in (1.0, 10.0, 30.0):
            for ratio in (1.4, 2.0, 2.5):
                for catalyst in ("Ni/Al2O3", "Ni-MgO", "Rh", "Pt", "none", "other"):
                    row = _point(
                        temperature_c=temperature,
                        pressure_bar=pressure,
                        ch4_o2_ratio=ratio,
                        catalyst=catalyst,
                    )
                    assert abs(row["balance_error_pct"]) < 1e-6


def test_simulated_points_stay_inside_contract_bounds() -> None:
    row = _point(temperature_c=500.0, pressure_bar=30.0, ghsv_per_h=100000.0, catalyst="none")

    assert 0.0 <= row["ch4_conversion"] <= 1.0
    assert 0.0 <= row["co2_conversion"] <= 1.0
    assert 0.0 <= row["o2_conversion"] <= 1.0
    assert 0.0 <= row["h2_yield_mol_per_mol_ch4"] <= 4.0
    assert 0.0 < row["co_yield_mol_per_mol_ch4"] <= 4.0
    assert 0.0 <= row["carbon_deposition_mg_per_gcat"] <= 100.0
    assert row["h2_co_ratio"] > 0.0


def test_generator_version_is_stable() -> None:
    assert GENERATOR_VERSION == "1.0.0"
