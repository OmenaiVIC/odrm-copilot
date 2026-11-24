from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from sqlalchemy.orm import Session, sessionmaker

from odrm.api.schemas import TeaRequest, TeaResponse
from odrm.api.screening import run_screening
from odrm.auth.models import Base
from odrm.db import create_db_engine
from odrm.evidence.models import EVIDENCE_BATCH_MAX_LEAVES
from odrm.evidence.repository import SqlAlchemyEvidenceRepository
from odrm.evidence.service import (
    EvidenceNotFoundError,
    EvidenceService,
    compute_hashes,
    merkle_root,
    verify_merkle_proof,
)
from odrm.reporting.content import build_report_data

pytestmark = pytest.mark.integration

BASE_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
HEX64 = re.compile(r"^[0-9a-f]{64}$")

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


def tea_request() -> TeaRequest:
    return TeaRequest.model_validate(
        {"conditions": dict(CONDITIONS), "assumptions": dict(ASSUMPTIONS)}
    )


def tea_response(
    *,
    ch4_conversion: float = 0.87,
    syngas_yield: float = 2.5,
) -> TeaResponse:
    models = {
        "ch4_conversion": (StubModel(ch4_conversion), {"model_version": "v-ch4"}),
        "syngas_yield_mol_per_mol_ch4": (
            StubModel(syngas_yield),
            {"model_version": "v-syngas"},
        ),
    }
    return run_screening(tea_request(), models)


def distinct_response(index: int) -> TeaResponse:
    return tea_response(syngas_yield=2.0 + index * 0.001)


def reference_root(screening_hashes: list[str]) -> str:
    level = [
        hashlib.sha256(b"\x00" + bytes.fromhex(value)).digest()
        for value in screening_hashes
    ]
    while len(level) > 1:
        parents = [
            hashlib.sha256(b"\x01" + level[index] + level[index + 1]).digest()
            for index in range(0, len(level) - 1, 2)
        ]
        if len(level) % 2:
            parents.append(level[-1])
        level = parents
    return level[0].hex()


@pytest.fixture()
def session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'evidence.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def repository(
    session_factory: sessionmaker[Session],
) -> SqlAlchemyEvidenceRepository:
    return SqlAlchemyEvidenceRepository(session_factory, root_builder=merkle_root)


@pytest.fixture()
def service(repository: SqlAlchemyEvidenceRepository) -> EvidenceService:
    return EvidenceService(repository)


def test_screening_produces_evidence_row(
    service: EvidenceService,
    repository: SqlAlchemyEvidenceRepository,
) -> None:
    recorded = service.record_screening(tea_request(), tea_response(), now=BASE_TIME)

    record = repository.get_by_screening_hash(recorded.screening_hash)
    assert record is not None
    assert record.screening_id == recorded.screening_id
    assert record.batch_id == recorded.batch_id
    assert HEX64.fullmatch(record.input_hash)
    assert HEX64.fullmatch(record.output_hash)
    assert HEX64.fullmatch(record.screening_hash)
    expected = hashlib.sha256(
        bytes.fromhex(record.input_hash) + bytes.fromhex(record.output_hash)
    ).hexdigest()
    assert record.screening_hash == expected

    leaves = repository.list_leaves(recorded.batch_id)
    assert [leaf.screening_hash for leaf in leaves] == [record.screening_hash]

    batch = repository.get_batch(recorded.batch_id)
    assert batch is not None
    assert batch.leaf_count == 1
    assert batch.merkle_root == merkle_root([record.screening_hash])
    assert batch.anchor_status == "pending"


@pytest.mark.parametrize("leaf_count", [1, 2, 3, 4])
def test_batch_root_computation(leaf_count: int) -> None:
    hashes = [f"{index + 1:064x}" for index in range(leaf_count)]

    root = merkle_root(hashes)

    assert HEX64.fullmatch(root)
    assert root == reference_root(hashes)
    if leaf_count == 1:
        assert root != hashes[0]


def test_batch_root_computation_rejects_empty_batch() -> None:
    with pytest.raises(ValueError):
        merkle_root([])


def test_verify_valid_hash(service: EvidenceService) -> None:
    recorded = [
        service.record_screening(
            tea_request(),
            distinct_response(index),
            now=BASE_TIME + timedelta(seconds=index),
        )
        for index in range(5)
    ]

    for item in recorded:
        proof = service.verify(item.screening_hash)
        assert proof.verified is True
        assert proof.screening_hash == item.screening_hash
        assert proof.batch_id == item.batch_id
        assert proof.leaf_count == 5
        assert 0 <= proof.leaf_index < 5
        assert all(HEX64.fullmatch(node) for node in proof.proof_path)
        assert verify_merkle_proof(
            item.screening_hash,
            proof.proof_path,
            proof.merkle_root,
            proof.leaf_index,
            proof.leaf_count,
        )


def test_verify_invalid_hash(service: EvidenceService) -> None:
    with pytest.raises(EvidenceNotFoundError):
        service.verify("f" * 64)

    recorded = service.record_screening(tea_request(), tea_response(), now=BASE_TIME)
    proof = service.verify(recorded.screening_hash)
    assert proof.leaf_count == 1
    assert proof.proof_path == []

    assert (
        verify_merkle_proof(
            recorded.screening_hash,
            ["00" * 32],
            proof.merkle_root,
            proof.leaf_index,
            proof.leaf_count,
        )
        is False
    )
    assert (
        verify_merkle_proof(
            recorded.screening_hash,
            proof.proof_path,
            "00" * 32,
            proof.leaf_index,
            proof.leaf_count,
        )
        is False
    )


def test_batch_anchoring_status_transitions(
    service: EvidenceService,
    repository: SqlAlchemyEvidenceRepository,
) -> None:
    first = service.record_screening(tea_request(), distinct_response(0), now=BASE_TIME)
    second = service.record_screening(
        tea_request(),
        distinct_response(1),
        now=BASE_TIME + timedelta(seconds=1),
    )

    assert first.batch_id == second.batch_id
    batch = repository.get_batch(first.batch_id)
    assert batch is not None
    assert batch.anchor_status == "pending"


def test_batch_rollover_at_100_leaves(
    service: EvidenceService,
    repository: SqlAlchemyEvidenceRepository,
) -> None:
    recorded = [
        service.record_screening(
            tea_request(),
            distinct_response(index),
            now=BASE_TIME + timedelta(seconds=index),
        )
        for index in range(EVIDENCE_BATCH_MAX_LEAVES)
    ]

    first_batch_id = recorded[0].batch_id
    assert {item.batch_id for item in recorded} == {first_batch_id}

    overflow = service.record_screening(
        tea_request(),
        distinct_response(EVIDENCE_BATCH_MAX_LEAVES),
        now=BASE_TIME + timedelta(seconds=EVIDENCE_BATCH_MAX_LEAVES),
    )
    assert overflow.batch_id != first_batch_id

    first_batch = repository.get_batch(first_batch_id)
    assert first_batch is not None
    assert first_batch.leaf_count == EVIDENCE_BATCH_MAX_LEAVES
    leaves = repository.list_leaves(first_batch_id)
    assert first_batch.merkle_root == merkle_root(
        [leaf.screening_hash for leaf in leaves]
    )

    second_batch = repository.get_batch(overflow.batch_id)
    assert second_batch is not None
    assert second_batch.leaf_count == 1
    assert second_batch.anchor_status == "pending"

    following = service.record_screening(
        tea_request(),
        distinct_response(EVIDENCE_BATCH_MAX_LEAVES + 1),
        now=BASE_TIME + timedelta(seconds=EVIDENCE_BATCH_MAX_LEAVES + 1),
    )
    assert following.batch_id == overflow.batch_id
    updated_second = repository.get_batch(overflow.batch_id)
    assert updated_second is not None
    assert updated_second.leaf_count == 2


def test_batch_rollover_on_new_utc_day(
    service: EvidenceService,
) -> None:
    first = service.record_screening(tea_request(), distinct_response(0), now=BASE_TIME)
    same_day = service.record_screening(
        tea_request(),
        distinct_response(1),
        now=BASE_TIME + timedelta(hours=1),
    )
    assert same_day.batch_id == first.batch_id

    next_day = service.record_screening(
        tea_request(),
        distinct_response(2),
        now=BASE_TIME + timedelta(days=1),
    )
    assert next_day.batch_id != first.batch_id

    later = service.record_screening(
        tea_request(),
        distinct_response(3),
        now=BASE_TIME + timedelta(days=1, hours=1),
    )
    assert later.batch_id == next_day.batch_id

    backwards = service.record_screening(
        tea_request(),
        distinct_response(4),
        now=BASE_TIME,
    )
    assert backwards.batch_id == next_day.batch_id


def test_canonical_hash_ignores_report_envelope() -> None:
    request = tea_request()
    response = tea_response()

    first = build_report_data(
        request,
        response,
        report_id="alpha",
        generated_at=BASE_TIME,
    )
    second = build_report_data(
        request,
        response,
        report_id="beta",
        generated_at=BASE_TIME + timedelta(hours=5),
    )

    assert first.sha256 != second.sha256
    assert compute_hashes(request, first.response) == compute_hashes(
        request, second.response
    )
