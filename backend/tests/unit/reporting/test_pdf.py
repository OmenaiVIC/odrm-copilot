from __future__ import annotations

import io
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pypdf import PdfReader

from odrm.api.schemas import TeaRequest
from odrm.api.screening import run_screening
from odrm.reporting.content import ReportData, build_report_data
from odrm.reporting.pdf import render_pdf

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
GENERATED_AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


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


def make_report(assumptions: dict[str, Any] | None = None) -> ReportData:
    payload = {
        "conditions": dict(CONDITIONS),
        "assumptions": dict(ASSUMPTIONS if assumptions is None else assumptions),
    }
    request = TeaRequest.model_validate(payload)
    response = run_screening(request, stub_models())
    return build_report_data(
        request,
        response,
        report_id=REPORT_ID,
        generated_at=GENERATED_AT,
    )


def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = " ".join(page.extract_text() or "" for page in reader.pages)
    return re.sub(r"\s+", " ", text)


def test_pdf_has_magic_bytes_and_eof_marker() -> None:
    pdf = render_pdf(make_report())

    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")


def test_pdf_is_at_least_two_pages() -> None:
    reader = PdfReader(io.BytesIO(render_pdf(make_report())))

    assert len(reader.pages) >= 2


def test_pdf_contains_report_identity_and_key_numbers() -> None:
    report = make_report()
    text = extract_text(render_pdf(report))

    assert "ODRM-Copilot" in text
    assert "ESG Screening Report" in text
    assert REPORT_ID in text
    assert "2026-01-02T03:04:05Z" in text
    assert report.sha256 in text
    assert "87" in text
    assert "6,037,806" in text


def test_pdf_renders_no_warnings_message() -> None:
    report = make_report()

    assert report.response.warnings == []
    assert "No warnings were generated" in extract_text(render_pdf(report))


def test_pdf_renders_negative_cash_flow_warning_and_unavailable_payback() -> None:
    assumptions = dict(ASSUMPTIONS)
    assumptions["syngas_price_usd_per_kmol"] = 0.0
    assumptions["carbon_credit_price_usd_per_tonne_co2e"] = 0.0
    text = extract_text(render_pdf(make_report(assumptions)))

    assert "Annual net cash flow is negative" in text
    assert "Not available" in text


def test_render_pdf_writes_no_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    render_pdf(make_report())

    assert list(tmp_path.rglob("*")) == []
