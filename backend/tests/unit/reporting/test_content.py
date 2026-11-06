from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pytest

from odrm.api.schemas import TeaRequest
from odrm.api.screening import run_screening
from odrm.reporting.content import (
    SCHEMA_VERSION,
    WARNING_MESSAGES,
    build_report_data,
    format_optional,
    safe_report_text,
)

CONDITIONS: dict[str, Any] = {
    "temperature_c": 800.0,
    "pressure_bar": 10.0,
    "ch4_o2_ratio": 2.0,
    "co2_ch4_ratio": 0.5,
    "h2o_ch4_ratio": 0.2,
    "ghsv_per_h": 5000.0,
    "catalyst": "Ni/Al2O3",
    "catalyst_loading_wt_pct": 10.0,
    "n2_dilution_mol_pct": None,
}

ASSUMPTIONS: dict[str, Any] = {
    "ch4_feed_kmol_per_h": 100.0,
    "natural_gas_price_usd_per_mmbtu": 3.0,
    "syngas_price_usd_per_kmol": 4.0,
    "carbon_credit_price_usd_per_tonne_co2e": 25.0,
    "co2_utilization_fraction": 0.4,
    "capex_usd": 5_000_000.0,
    "opex_pct_of_capex_per_year": 5.0,
    "operating_hours_per_day": 24.0,
    "operating_days_per_year": 330.0,
}

REPORT_ID = "11111111-1111-4111-8111-111111111111"
GENERATED_AT = datetime(2026, 1, 2, 3, 4, 5, 999999, tzinfo=UTC)
GENERATED_AT_TEXT = "2026-01-02T03:04:05Z"


class StubModel:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, frame: Any) -> np.ndarray:
        return np.array([self.value])


def stub_models() -> dict[str, tuple[Any, dict[str, Any]]]:
    return {
        "ch4_conversion": (StubModel(0.87), {"model_version": "v-ch4"}),
        "syngas_yield_mol_per_mol_ch4": (StubModel(2.5), {"model_version": "v-syngas"}),
    }


def make_request() -> TeaRequest:
    return TeaRequest.model_validate({"conditions": dict(CONDITIONS), "assumptions": dict(ASSUMPTIONS)})


def make_report(warnings: list[str] | None = None) -> Any:
    request = make_request()
    response = run_screening(request, stub_models())
    if warnings is not None:
        response = response.model_copy(update={"warnings": warnings})
    return build_report_data(
        request,
        response,
        report_id=REPORT_ID,
        generated_at=GENERATED_AT,
    )


def test_report_data_contains_full_screening_context() -> None:
    report = make_report()

    assert report.report_id == REPORT_ID
    assert report.generated_at == GENERATED_AT_TEXT
    assert report.schema_version == SCHEMA_VERSION == "esg-report/v1"
    assert report.request.conditions.catalyst == "Ni/Al2O3"
    assert report.request.conditions.n2_dilution_mol_pct is None
    assert report.request.assumptions.capex_usd == pytest.approx(5_000_000.0)
    assert report.response.predictions == pytest.approx(
        {"ch4_conversion": 0.87, "syngas_yield_mol_per_mol_ch4": 2.5}
    )
    assert report.response.model_versions == {"ch4_conversion": "v-ch4", "syngas_yield_mol_per_mol_ch4": "v-syngas"}
    assert report.response.financials.annual_net_cash_flow_usd is not None
    assert report.canonical_payload
    assert len(report.sha256) == 64


def test_optional_values_render_not_provided() -> None:
    assert format_optional(None) == "Not provided"
    assert format_optional(10.0) == "10"
    assert format_optional(0.0) == "0"
    assert format_optional("Ni/Al2O3") == "Ni/Al2O3"


def test_canonical_payload_contains_every_request_and_response_field() -> None:
    report = make_report()
    payload = json.loads(report.canonical_payload)

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["report_id"] == REPORT_ID
    assert payload["generated_at"] == GENERATED_AT_TEXT
    assert payload["request"] == report.request.model_dump(mode="json")
    assert payload["response"] == report.response.model_dump(mode="json")
    assert set(payload["response"]["financials"]) == set(report.response.financials.model_dump())


def test_all_known_warning_codes_map_to_human_messages() -> None:
    codes = [
        "carbon_credit_not_included",
        "negative_annual_cash_flow",
        "syngas_yield_out_of_envelope",
        "zero_syngas_price",
        "zero_carbon_price",
    ]
    report = make_report(warnings=codes)

    assert [warning.code for warning in report.warnings] == codes
    for warning in report.warnings:
        assert warning.message == WARNING_MESSAGES[warning.code]
        assert warning.message


def test_unknown_warning_code_falls_back_to_raw_code() -> None:
    report = make_report(warnings=["future_warning"])

    assert len(report.warnings) == 1
    assert report.warnings[0].code == "future_warning"
    assert report.warnings[0].message == "future_warning"


def test_canonical_json_is_stable_regardless_of_dict_order() -> None:
    report = make_report()
    response = report.response.model_copy(
        update={
            "predictions": dict(reversed(list(report.response.predictions.items()))),
            "model_versions": dict(reversed(list(report.response.model_versions.items()))),
        }
    )
    reordered = build_report_data(
        report.request,
        response,
        report_id=REPORT_ID,
        generated_at=GENERATED_AT,
    )

    assert reordered.canonical_payload == report.canonical_payload
    assert reordered.sha256 == report.sha256


def test_digest_matches_independently_computed_sha256() -> None:
    report = make_report()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "generated_at": GENERATED_AT_TEXT,
        "request": report.request.model_dump(mode="json"),
        "response": report.response.model_dump(mode="json"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    assert report.canonical_payload == canonical
    assert report.sha256 == expected


def test_digest_changes_when_any_input_changes() -> None:
    base = make_report()
    changed_request = base.request.model_copy(
        update={
            "assumptions": base.request.assumptions.model_copy(update={"capex_usd": 6_000_000.0})
        }
    )
    changed_response = base.response.model_copy(
        update={"warnings": ["negative_annual_cash_flow"]}
    )

    variants = {
        build_report_data(
            changed_request, base.response, report_id=REPORT_ID, generated_at=GENERATED_AT
        ).sha256,
        build_report_data(
            base.request, changed_response, report_id=REPORT_ID, generated_at=GENERATED_AT
        ).sha256,
        build_report_data(
            base.request, base.response, report_id="22222222-2222-4222-8222-222222222222",
            generated_at=GENERATED_AT,
        ).sha256,
        build_report_data(
            base.request, base.response, report_id=REPORT_ID,
            generated_at=datetime(2026, 1, 2, 3, 4, 6, tzinfo=UTC),
        ).sha256,
    }

    assert base.sha256 not in variants
    assert len(variants) == 4


def test_safe_report_text_blocks_markup_and_truncates() -> None:
    hostile = "<b>Ni/Al₂O₃</b><script>alert(1)</script>"
    rendered = safe_report_text(hostile, max_length=40)

    assert "<" not in rendered
    assert ">" not in rendered
    assert "&lt;" in rendered
    assert len(safe_report_text("A" * 100, max_length=40)) == 40

    ascii_rendered = safe_report_text("Ni/Al₂O₃")
    assert ascii_rendered == "Ni/Al2O3"
