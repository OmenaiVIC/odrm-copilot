from __future__ import annotations

from odrm.domain.tea import TeaInputs
from odrm.domain.tea_defaults import (
    DEFAULT_CO2_UTILIZATION_FRACTION,
    DEFAULT_OPERATING_DAYS_PER_YEAR,
    DEFAULT_OPERATING_HOURS_PER_DAY,
    DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR,
    ENGINEERING_DEFAULT_PROVENANCE,
)


def test_engineering_default_values() -> None:
    assert DEFAULT_OPERATING_HOURS_PER_DAY == 24.0
    assert DEFAULT_OPERATING_DAYS_PER_YEAR == 330.0
    assert DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR == 5.0
    assert DEFAULT_CO2_UTILIZATION_FRACTION == 0.0


def test_provenance_covers_every_default() -> None:
    assert set(ENGINEERING_DEFAULT_PROVENANCE) == {
        "DEFAULT_OPERATING_HOURS_PER_DAY",
        "DEFAULT_OPERATING_DAYS_PER_YEAR",
        "DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR",
        "DEFAULT_CO2_UTILIZATION_FRACTION",
    }
    assert all(text.strip() for text in ENGINEERING_DEFAULT_PROVENANCE.values())


def test_no_market_price_defaults() -> None:
    assert not any("price" in name.lower() for name in ENGINEERING_DEFAULT_PROVENANCE)
    assert not any("price" in text.lower() for text in ENGINEERING_DEFAULT_PROVENANCE.values())


def test_tea_inputs_use_engineering_defaults() -> None:
    inputs = TeaInputs(
        syngas_yield_mol_per_mol_ch4=2.5,
        ch4_feed_kmol_per_h=100.0,
        co2_ch4_ratio=0.5,
        natural_gas_price_usd_per_mmbtu=3.0,
        syngas_price_usd_per_kmol=4.0,
        carbon_credit_price_usd_per_tonne_co2e=25.0,
        capex_usd=5_000_000.0,
    )
    assert inputs.operating_hours_per_day == DEFAULT_OPERATING_HOURS_PER_DAY
    assert inputs.operating_days_per_year == DEFAULT_OPERATING_DAYS_PER_YEAR
    assert inputs.opex_pct_of_capex_per_year == DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR
    assert inputs.co2_utilization_fraction == DEFAULT_CO2_UTILIZATION_FRACTION
