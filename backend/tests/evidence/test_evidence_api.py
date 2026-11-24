from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from odrm.api.schemas import TeaRequest, TeaResponse
from odrm.api.screening import run_screening
from odrm.auth.models import Base
from odrm.core.config import Settings
from odrm.db import create_db_engine
from odrm.evidence.repository import RecordedEvidence, SqlAlchemyEvidenceRepository
from odrm.evidence.service import compute_hashes, merkle_root
from odrm.main import create_app

pytestmark = pytest.mark.integration

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


def tea_payload() -> dict[str, Any]:
    return {"conditions": dict(CONDITIONS), "assumptions": dict(ASSUMPTIONS)}


def stub_models(
    ch4_conversion: float = 0.87,
    syngas_yield: float = 2.5,
) -> dict[str, tuple[Any, dict[str, Any]]]:
    return {
        "ch4_conversion": (StubModel(ch4_conversion), {"model_version": "v-ch4"}),
        "syngas_yield_mol_per_mol_ch4": (
            StubModel(syngas_yield),
            {"model_version": "v-syngas"},
        ),
    }


class FailingEvidenceRepository:
    def record_screening(self, **_: Any) -> RecordedEvidence:
        raise RuntimeError("ledger down")

    def get_by_screening_hash(self, screening_hash: str) -> None:
        raise AssertionError("read path must not be used")

    def get_batch(self, batch_id: str) -> None:
        raise AssertionError("read path must not be used")

    def list_leaves(self, batch_id: str) -> list[Any]:
        raise AssertionError("read path must not be used")


@pytest.fixture()
def evidence_session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'evidence-api.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def evidence_repository(
    evidence_session_factory: sessionmaker[Session],
) -> SqlAlchemyEvidenceRepository:
    return SqlAlchemyEvidenceRepository(
        evidence_session_factory,
        root_builder=merkle_root,
    )


@pytest.fixture()
def evidence_app(
    test_settings: Settings,
    auth_repository: Any,
    evidence_repository: SqlAlchemyEvidenceRepository,
) -> Any:
    app = create_app(
        settings=test_settings,
        user_repository=auth_repository,
        evidence_repository=evidence_repository,
    )
    app.state.models = stub_models()
    return app


@pytest.fixture()
def evidence_client(
    evidence_app: Any,
    auth_headers: dict[str, str],
) -> Iterator[TestClient]:
    with TestClient(evidence_app, headers=auth_headers) as client:
        yield client


@pytest.fixture()
def anonymous_evidence_client(evidence_app: Any) -> Iterator[TestClient]:
    with TestClient(evidence_app) as client:
        yield client


@pytest.fixture()
def failing_evidence_app(
    test_settings: Settings,
    auth_repository: Any,
) -> Any:
    app = create_app(
        settings=test_settings,
        user_repository=auth_repository,
        evidence_repository=FailingEvidenceRepository(),
    )
    app.state.models = stub_models()
    return app


def test_tea_creates_evidence_row(
    evidence_client: TestClient,
    evidence_repository: SqlAlchemyEvidenceRepository,
) -> None:
    payload = tea_payload()
    response = evidence_client.post("/api/v1/tea", json=payload)

    assert response.status_code == 200
    assert response.headers["x-evidence-status"] == "recorded"

    request = TeaRequest.model_validate(payload)
    screening = TeaResponse.model_validate(response.json())
    _, _, screening_hash = compute_hashes(request, screening)

    record = evidence_repository.get_by_screening_hash(screening_hash)
    assert record is not None
    assert record.batch is not None
    assert record.batch.leaf_count == 1


def test_report_creates_evidence_row(
    evidence_client: TestClient,
    evidence_app: Any,
    evidence_repository: SqlAlchemyEvidenceRepository,
) -> None:
    payload = tea_payload()
    response = evidence_client.post(
        "/api/v1/report",
        json=payload,
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert response.headers["x-evidence-status"] == "recorded"
    exposed = response.headers["access-control-expose-headers"].lower()
    assert "x-evidence-status" in exposed

    request = TeaRequest.model_validate(payload)
    screening = run_screening(request, evidence_app.state.models)
    _, _, screening_hash = compute_hashes(request, screening)

    record = evidence_repository.get_by_screening_hash(screening_hash)
    assert record is not None
    assert record.screening_id


def test_evidence_api_verify_endpoint(
    evidence_client: TestClient,
    anonymous_evidence_client: TestClient,
    evidence_repository: SqlAlchemyEvidenceRepository,
) -> None:
    payload = tea_payload()
    tea = evidence_client.post("/api/v1/tea", json=payload)
    assert tea.status_code == 200

    request = TeaRequest.model_validate(payload)
    screening = TeaResponse.model_validate(tea.json())
    _, _, screening_hash = compute_hashes(request, screening)

    response = evidence_client.get(f"/api/v1/evidence/verify/{screening_hash}")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "screening_hash",
        "batch_id",
        "merkle_root",
        "proof_path",
        "leaf_index",
        "leaf_count",
        "verified",
    }
    assert body["screening_hash"] == screening_hash
    assert body["verified"] is True
    assert body["leaf_count"] == 1
    assert body["leaf_index"] == 0
    assert body["proof_path"] == []

    record = evidence_repository.get_by_screening_hash(screening_hash)
    assert record is not None
    assert body["batch_id"] == record.batch_id
    assert body["merkle_root"] == merkle_root([screening_hash])

    missing = evidence_client.get(f"/api/v1/evidence/verify/{'0' * 64}")
    assert missing.status_code == 404
    assert missing.json() == {
        "detail": {
            "code": "EVIDENCE_NOT_FOUND",
            "message": "No evidence exists for this screening hash.",
        }
    }

    anonymous = anonymous_evidence_client.get(
        f"/api/v1/evidence/verify/{screening_hash}"
    )
    assert anonymous.status_code == 401

    malformed = evidence_client.get("/api/v1/evidence/verify/not-a-hash")
    assert malformed.status_code == 422


def test_tea_evidence_failure_is_fail_open(
    failing_evidence_app: Any,
    auth_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        caplog.at_level(logging.WARNING, logger="odrm.api.routes"),
        TestClient(failing_evidence_app, headers=auth_headers) as client,
    ):
        response = client.post("/api/v1/tea", json=tea_payload())

    assert response.status_code == 200
    assert response.headers["x-evidence-status"] == "failed"
    assert response.json()["predictions"]["ch4_conversion"] == pytest.approx(0.87)
    assert "Evidence recording failed" in caplog.text
    assert "Ni/Al2O3" not in caplog.text


def test_report_evidence_failure_is_fail_open(
    failing_evidence_app: Any,
    auth_headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        caplog.at_level(logging.WARNING, logger="odrm.api.report"),
        TestClient(failing_evidence_app, headers=auth_headers) as client,
    ):
        response = client.post("/api/v1/report", json=tea_payload())

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert response.headers["x-evidence-status"] == "failed"
    assert "Evidence recording failed" in caplog.text
    assert "Ni/Al2O3" not in caplog.text
