from __future__ import annotations

import logging
import math
import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from odrm.api.schemas import TeaRequest, TeaResponse
from odrm.main import create_app
from odrm.reporting.content import build_report_data

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


class StubModel:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, frame: Any) -> np.ndarray:
        return np.array([self.value])


def report_payload() -> dict[str, Any]:
    return {"conditions": dict(CONDITIONS), "assumptions": dict(ASSUMPTIONS)}


def stub_models(
    ch4_conversion: float = 0.87, syngas_yield: float = 2.5
) -> dict[str, tuple[Any, dict[str, Any]]]:
    return {
        "ch4_conversion": (StubModel(ch4_conversion), {"model_version": "v-ch4"}),
        "syngas_yield_mol_per_mol_ch4": (
            StubModel(syngas_yield),
            {"model_version": "v-syngas"},
        ),
    }


@pytest.fixture()
def report_app() -> Any:
    app = create_app()
    app.state.models = stub_models()
    return app


@pytest.fixture()
def report_client(report_app: Any) -> Iterator[TestClient]:
    with TestClient(report_app) as client:
        yield client


def test_report_endpoint_returns_pdf_with_compliance_headers(report_client: TestClient) -> None:
    response = report_client.post("/api/v1/report", json=report_payload())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")

    disposition = response.headers["content-disposition"]
    match = re.fullmatch(
        r'attachment; filename="odrm-esg-report-([0-9a-f-]{36})\.pdf"',
        disposition,
    )
    assert match is not None
    report_id = response.headers["x-report-id"]
    assert match.group(1) == report_id
    assert uuid.UUID(report_id).version == 4

    digest = response.headers["x-report-sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", digest)

    generated_at = response.headers["x-report-generated-at"]
    assert generated_at.endswith("Z")
    parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is UTC
    assert parsed.microsecond == 0


def test_report_numbers_and_digest_match_tea(report_client: TestClient) -> None:
    payload = report_payload()
    tea_response = report_client.post("/api/v1/tea", json=payload)
    report_response = report_client.post("/api/v1/report", json=payload)

    assert tea_response.status_code == 200
    assert report_response.status_code == 200

    request = TeaRequest.model_validate(payload)
    response = TeaResponse.model_validate(tea_response.json())
    report_id = report_response.headers["x-report-id"]
    generated_at = report_response.headers["x-report-generated-at"]
    expected = build_report_data(
        request,
        response,
        report_id=report_id,
        generated_at=datetime.fromisoformat(generated_at.replace("Z", "+00:00")),
    )

    assert report_response.headers["x-report-sha256"] == expected.sha256
    assert expected.response.predictions["ch4_conversion"] == pytest.approx(0.87)
    assert expected.response.financials.annual_net_cash_flow_usd == pytest.approx(
        6_037_806.8
    )


def test_report_invalid_conditions_return_422(report_client: TestClient) -> None:
    payload = report_payload()
    payload["conditions"]["temperature_c"] = 1200.0

    response = report_client.post("/api/v1/report", json=payload)

    assert response.status_code == 422


def test_report_invalid_assumptions_return_422(report_client: TestClient) -> None:
    payload = report_payload()
    payload["assumptions"]["capex_usd"] = 0.0

    response = report_client.post("/api/v1/report", json=payload)

    assert response.status_code == 422


def test_report_extra_top_level_field_returns_422(report_client: TestClient) -> None:
    payload = report_payload()
    payload["unknown"] = 1.0

    response = report_client.post("/api/v1/report", json=payload)

    assert response.status_code == 422


def test_report_missing_models_return_503(report_app: Any) -> None:
    report_app.state.models = {}
    with TestClient(report_app) as client:
        response = client.post("/api/v1/report", json=report_payload())

    assert response.status_code == 503
    assert "Model unavailable" in response.json()["detail"]


def test_report_partial_models_return_503(report_app: Any) -> None:
    models = stub_models()
    models.pop("syngas_yield_mol_per_mol_ch4")
    report_app.state.models = models
    with TestClient(report_app) as client:
        response = client.post("/api/v1/report", json=report_payload())

    assert response.status_code == 503


def test_report_non_finite_prediction_returns_500_without_pdf(report_app: Any) -> None:
    report_app.state.models = stub_models(syngas_yield=math.nan)
    with TestClient(report_app) as client:
        response = client.post("/api/v1/report", json=report_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Model prediction failed."}
    assert not response.content.startswith(b"%PDF-")


def test_report_rendering_failure_returns_generic_500(
    report_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(report: Any) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr("odrm.api.report.render_pdf", explode)
    response = report_client.post("/api/v1/report", json=report_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Report generation failed."}
    assert not response.content.startswith(b"%PDF-")


def test_report_error_logs_do_not_contain_request_payload(
    report_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def explode(report: Any) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr("odrm.api.report.render_pdf", explode)
    with caplog.at_level(logging.ERROR, logger="odrm.api.report"):
        response = report_client.post("/api/v1/report", json=report_payload())

    assert response.status_code == 500
    body = response.text
    log_text = caplog.text
    for secret in ("Ni/Al2O3", "5000000", "100.0"):
        assert secret not in body
        assert secret not in log_text


def test_report_response_exposes_compliance_headers_to_browsers(
    report_client: TestClient,
) -> None:
    response = report_client.post(
        "/api/v1/report",
        json=report_payload(),
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    exposed = response.headers["access-control-expose-headers"].lower()
    for header in (
        "content-disposition",
        "x-report-id",
        "x-report-sha256",
        "x-report-generated-at",
    ):
        assert header in exposed
