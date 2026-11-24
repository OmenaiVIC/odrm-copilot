from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from odrm.evidence.models import (
    EVIDENCE_BATCH_MAX_LEAVES,
    EvidenceBatch,
    ScreeningEvidence,
)

_ADVISORY_LOCK_KEY = 0x0D2E1DCE

RootBuilder = Callable[[Sequence[str]], str]


@dataclass(frozen=True)
class RecordedEvidence:
    screening_id: str
    screening_hash: str
    batch_id: str


@dataclass(frozen=True)
class EvidenceBatchRecord:
    id: str
    merkle_root: str
    leaf_count: int
    created_at: datetime
    anchor_status: str


@dataclass(frozen=True)
class EvidenceLeafRecord:
    id: str
    screening_id: str
    input_hash: str
    output_hash: str
    screening_hash: str
    batch_id: str
    created_at: datetime


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    screening_id: str
    input_hash: str
    output_hash: str
    screening_hash: str
    batch_id: str
    created_at: datetime
    batch: EvidenceBatchRecord | None


class EvidenceRepository(Protocol):
    def record_screening(
        self,
        *,
        screening_id: str,
        input_hash: str,
        output_hash: str,
        screening_hash: str,
        now: datetime | None = None,
    ) -> RecordedEvidence: ...

    def get_by_screening_hash(self, screening_hash: str) -> EvidenceRecord | None: ...

    def get_batch(self, batch_id: str) -> EvidenceBatchRecord | None: ...

    def list_leaves(self, batch_id: str) -> list[EvidenceLeafRecord]: ...


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _batch_record(batch: EvidenceBatch) -> EvidenceBatchRecord:
    return EvidenceBatchRecord(
        id=batch.id,
        merkle_root=batch.merkle_root,
        leaf_count=batch.leaf_count,
        created_at=_as_utc(batch.created_at),
        anchor_status=batch.anchor_status,
    )


def _leaf_record(leaf: ScreeningEvidence) -> EvidenceLeafRecord:
    return EvidenceLeafRecord(
        id=leaf.id,
        screening_id=leaf.screening_id,
        input_hash=leaf.input_hash,
        output_hash=leaf.output_hash,
        screening_hash=leaf.screening_hash,
        batch_id=leaf.batch_id,
        created_at=_as_utc(leaf.created_at),
    )


def _evidence_record(
    leaf: ScreeningEvidence,
    batch: EvidenceBatch | None,
) -> EvidenceRecord:
    return EvidenceRecord(
        id=leaf.id,
        screening_id=leaf.screening_id,
        input_hash=leaf.input_hash,
        output_hash=leaf.output_hash,
        screening_hash=leaf.screening_hash,
        batch_id=leaf.batch_id,
        created_at=_as_utc(leaf.created_at),
        batch=_batch_record(batch) if batch is not None else None,
    )


class SqlAlchemyEvidenceRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        root_builder: RootBuilder,
    ) -> None:
        self._session_factory = session_factory
        self._root_builder = root_builder

    def record_screening(
        self,
        *,
        screening_id: str,
        input_hash: str,
        output_hash: str,
        screening_hash: str,
        now: datetime | None = None,
    ) -> RecordedEvidence:
        recorded_at = now or datetime.now(UTC)
        with self._session_factory() as session:
            self._lock(session)
            batch = session.scalar(
                select(EvidenceBatch)
                .order_by(
                    EvidenceBatch.created_at.desc(),
                    EvidenceBatch.id.desc(),
                )
                .limit(1)
                .with_for_update()
            )
            if batch is None or self._should_roll(batch, recorded_at):
                batch = EvidenceBatch(
                    merkle_root=self._root_builder([screening_hash]),
                    leaf_count=1,
                    created_at=recorded_at,
                    anchor_status="pending",
                )
                session.add(batch)
                session.flush()

            leaf = ScreeningEvidence(
                screening_id=screening_id,
                input_hash=input_hash,
                output_hash=output_hash,
                screening_hash=screening_hash,
                batch_id=batch.id,
                created_at=recorded_at,
            )
            session.add(leaf)
            session.flush()

            leaves = session.scalars(
                select(ScreeningEvidence)
                .where(ScreeningEvidence.batch_id == batch.id)
                .order_by(
                    ScreeningEvidence.created_at.asc(),
                    ScreeningEvidence.id.asc(),
                )
            ).all()
            screening_hashes = [item.screening_hash for item in leaves]
            batch.merkle_root = self._root_builder(screening_hashes)
            batch.leaf_count = len(screening_hashes)
            batch_id = batch.id
            session.commit()

        return RecordedEvidence(
            screening_id=screening_id,
            screening_hash=screening_hash,
            batch_id=batch_id,
        )

    def get_by_screening_hash(self, screening_hash: str) -> EvidenceRecord | None:
        with self._session_factory() as session:
            row = session.execute(
                select(ScreeningEvidence, EvidenceBatch)
                .outerjoin(
                    EvidenceBatch,
                    ScreeningEvidence.batch_id == EvidenceBatch.id,
                )
                .where(ScreeningEvidence.screening_hash == screening_hash)
                .order_by(
                    ScreeningEvidence.created_at.asc(),
                    ScreeningEvidence.id.asc(),
                )
                .limit(1)
            ).first()
            if row is None:
                return None
            leaf, batch = row
            return _evidence_record(leaf, batch)

    def get_batch(self, batch_id: str) -> EvidenceBatchRecord | None:
        with self._session_factory() as session:
            batch = session.get(EvidenceBatch, batch_id)
            return _batch_record(batch) if batch is not None else None

    def list_leaves(self, batch_id: str) -> list[EvidenceLeafRecord]:
        with self._session_factory() as session:
            leaves = session.scalars(
                select(ScreeningEvidence)
                .where(ScreeningEvidence.batch_id == batch_id)
                .order_by(
                    ScreeningEvidence.created_at.asc(),
                    ScreeningEvidence.id.asc(),
                )
            ).all()
            return [_leaf_record(leaf) for leaf in leaves]

    @staticmethod
    def _should_roll(batch: EvidenceBatch, now: datetime) -> bool:
        if batch.leaf_count >= EVIDENCE_BATCH_MAX_LEAVES:
            return True
        return now.date() > _as_utc(batch.created_at).date()

    @staticmethod
    def _lock(session: Session) -> None:
        if session.get_bind().dialect.name == "postgresql":
            session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": _ADVISORY_LOCK_KEY},
            )
