from __future__ import annotations

import os
import socket
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from odrm.core.config import Settings, get_settings
from odrm.main import create_app

os.environ.setdefault("ODRM_ENV", "test")

_ALLOWED_HOSTS = {"127.0.0.1", "::1", "localhost"}
_SEED = 7
_CREATED_AT_BASE = pd.Timestamp("2026-01-01T00:00:00Z")


class NetworkBlockedError(RuntimeError):
    """Raised when a test attempts an outbound network connection."""


class ToolSpy:
    """Records tool invocations so agent tests assert selection + arguments, not prose."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def record(self, name: str, **kwargs: Any) -> None:
        self.calls.append((name, kwargs))

    def called(self, name: str) -> bool:
        return any(call_name == name for call_name, _ in self.calls)


@pytest.fixture(scope="session", autouse=True)
def block_outbound_network() -> Iterator[None]:
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_create_connection = socket.create_connection

    def host_of(address: Any) -> str:
        if isinstance(address, tuple) and address:
            return str(address[0])
        return str(address)

    def guarded_connect(self: socket.socket, address: Any) -> Any:
        if host_of(address) not in _ALLOWED_HOSTS:
            raise NetworkBlockedError(f"Outbound network access blocked in tests: {address!r}")
        return real_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: Any) -> int:
        if host_of(address) not in _ALLOWED_HOSTS:
            raise NetworkBlockedError(f"Outbound network access blocked in tests: {address!r}")
        return real_connect_ex(self, address)

    def guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> socket.socket:
        if host_of(address) not in _ALLOWED_HOSTS:
            raise NetworkBlockedError(f"Outbound network access blocked in tests: {address!r}")
        return real_create_connection(address, *args, **kwargs)

    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign]
    socket.create_connection = guarded_create_connection  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = real_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = real_connect_ex  # type: ignore[method-assign]
        socket.create_connection = real_create_connection  # type: ignore[assignment]


@pytest.fixture(scope="session")
def test_settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    get_settings.cache_clear()
    return Settings(
        env="test",
        log_level="DEBUG",
        api_prefix="/api/v1",
        cors_origins="http://localhost:3000",
        model_dir=str(tmp_path_factory.mktemp("models")),
        data_dir=str(tmp_path_factory.mktemp("data")),
    )


@pytest.fixture(scope="session")
def app(test_settings: Settings) -> Any:
    return create_app(settings=test_settings)


@pytest.fixture()
def client(app: Any) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _risk_class(carbon_mg_per_gcat: np.ndarray) -> list[str]:
    classes: list[str] = []
    for value in carbon_mg_per_gcat:
        if value < 1.0:
            classes.append("none")
        elif value < 5.0:
            classes.append("low")
        elif value < 20.0:
            classes.append("moderate")
        else:
            classes.append("high")
    return classes


def make_odrm_frame(rows: int = 200, seed: int = _SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    ch4_conversion = rng.uniform(0.55, 0.99, rows)
    h2_yield = ch4_conversion * rng.uniform(1.6, 2.0, rows)
    co_yield = ch4_conversion * rng.uniform(0.7, 1.0, rows)
    h2_co_ratio = h2_yield / co_yield
    ghsv = rng.uniform(1_000.0, 100_000.0, rows)
    carbon = rng.gamma(0.8, 2.5, rows)

    frame = pd.DataFrame(
        {
            "run_id": [
                str(uuid.uuid5(uuid.NAMESPACE_URL, f"odrm/{seed}/{i}")) for i in range(rows)
            ],
            "created_at": pd.Series(
                [_CREATED_AT_BASE + pd.Timedelta(minutes=i) for i in range(rows)],
                dtype="datetime64[ns, UTC]",
            ),
            "source": "synthetic",
            "schema_version": "v1",
            "reactor_id": pd.array([None] * rows, dtype="string"),
            "catalyst": rng.choice(["Ni/Al2O3", "Ni-MgO", "Rh", "Pt", "none", "other"], size=rows),
            "catalyst_loading_wt_pct": rng.uniform(0.0, 20.0, rows),
            "temperature_c": rng.uniform(500.0, 1_000.0, rows),
            "pressure_bar": rng.uniform(1.0, 30.0, rows),
            "ch4_o2_ratio": rng.uniform(1.4, 2.5, rows),
            "co2_ch4_ratio": rng.uniform(0.0, 1.5, rows),
            "h2o_ch4_ratio": rng.uniform(0.0, 1.5, rows),
            "ghsv_per_h": ghsv,
            "n2_dilution_mol_pct": rng.uniform(0.0, 50.0, rows),
            "contact_time_ms": 3_600_000.0 / ghsv,
            "ch4_conversion": ch4_conversion,
            "co2_conversion": ch4_conversion * 0.4,
            "o2_conversion": np.minimum(ch4_conversion * 0.95, 0.99),
            "h2_yield_mol_per_mol_ch4": h2_yield,
            "co_yield_mol_per_mol_ch4": co_yield,
            "h2_co_ratio": h2_co_ratio,
            "syngas_yield_mol_per_mol_ch4": h2_yield + co_yield,
            "ch4_slip_pct": (1.0 - ch4_conversion) * 100.0,
            "carbon_deposition_mg_per_gcat": carbon,
            "carbon_risk_class": _risk_class(carbon),
            "energy_input_kw": rng.uniform(0.0, 100_000.0, rows),
            "balance_error_pct": rng.uniform(-2.0, 2.0, rows),
            "quality_flag": "valid",
            "notes": pd.array([None] * rows, dtype="string"),
        }
    )

    float_columns = [
        "catalyst_loading_wt_pct",
        "temperature_c",
        "pressure_bar",
        "ch4_o2_ratio",
        "co2_ch4_ratio",
        "h2o_ch4_ratio",
        "ghsv_per_h",
        "n2_dilution_mol_pct",
        "contact_time_ms",
        "ch4_conversion",
        "co2_conversion",
        "o2_conversion",
        "h2_yield_mol_per_mol_ch4",
        "co_yield_mol_per_mol_ch4",
        "h2_co_ratio",
        "syngas_yield_mol_per_mol_ch4",
        "ch4_slip_pct",
        "carbon_deposition_mg_per_gcat",
        "energy_input_kw",
        "balance_error_pct",
    ]
    frame[float_columns] = frame[float_columns].astype("float32")
    frame["source"] = frame["source"].astype("category")
    frame["catalyst"] = frame["catalyst"].astype("category")
    frame["carbon_risk_class"] = frame["carbon_risk_class"].astype("category")
    frame["quality_flag"] = frame["quality_flag"].astype("category")
    return frame.sort_values("created_at").reset_index(drop=True)


@pytest.fixture()
def odrm_row() -> dict[str, Any]:
    row = make_odrm_frame(rows=1).iloc[0].to_dict()
    row["reactor_id"] = None
    row["notes"] = None
    return row


@pytest.fixture()
def odrm_frame() -> pd.DataFrame:
    return make_odrm_frame()


@pytest.fixture()
def odrm_frame_bad(odrm_frame: pd.DataFrame) -> pd.DataFrame:
    bad = odrm_frame.head(5).copy()
    bad.loc[bad.index[0], "temperature_c"] = 1_200.0
    bad.loc[bad.index[1], "ch4_conversion"] = 1.5
    bad.loc[bad.index[2], "h2_yield_mol_per_mol_ch4"] = np.nan
    bad.loc[bad.index[3], "balance_error_pct"] = 9.0
    bad.loc[bad.index[4], "carbon_deposition_mg_per_gcat"] = -1.0
    return bad


@pytest.fixture()
def parquet_path(tmp_path: Any, odrm_frame: pd.DataFrame) -> Any:
    path = tmp_path / "odrm_fixture.parquet"
    odrm_frame.to_parquet(path, index=False)
    return path


@pytest.fixture(scope="session")
def tiny_model() -> Any:
    from xgboost import XGBRegressor

    rng = np.random.default_rng(_SEED)
    features = pd.DataFrame(
        {
            "temperature_c": rng.uniform(500.0, 1_000.0, 96),
            "pressure_bar": rng.uniform(1.0, 30.0, 96),
            "ch4_o2_ratio": rng.uniform(1.4, 2.5, 96),
            "co2_ch4_ratio": rng.uniform(0.0, 1.5, 96),
            "h2o_ch4_ratio": rng.uniform(0.0, 1.5, 96),
            "ghsv_per_h": rng.uniform(1_000.0, 100_000.0, 96),
        }
    )
    target = (
        0.4
        + 0.0004 * features["temperature_c"]
        + 0.02 * features["ch4_o2_ratio"]
        - 0.000002 * features["ghsv_per_h"]
    ).clip(0.0, 1.0)
    model = XGBRegressor(
        n_estimators=12,
        max_depth=3,
        learning_rate=0.2,
        random_state=_SEED,
        n_jobs=1,
    )
    model.fit(features, target)
    return model


@pytest.fixture()
def fake_llm() -> FakeListChatModel:
    return FakeListChatModel(
        responses=['{"tool": "predict_syngas", "args": {"temperature_c": 750.0}}']
    )


@pytest.fixture()
def tool_spy() -> ToolSpy:
    return ToolSpy()


@pytest.fixture()
def assert_valid_odrm_frame() -> Callable[[pd.DataFrame], None]:
    def check(frame: pd.DataFrame) -> None:
        assert len(frame) > 0
        assert frame["temperature_c"].between(500.0, 1_000.0).all()
        assert frame["ch4_conversion"].between(0.0, 1.0).all()
        assert frame["carbon_deposition_mg_per_gcat"].between(0.0, 100.0).all()
        assert frame[["run_id", "created_at", "source", "schema_version"]].notna().all().all()

    return check


@pytest.fixture()
def assert_tool_called() -> Callable[..., None]:
    def check(spy: ToolSpy, name: str, **expected_args: Any) -> None:
        matching = [kwargs for call_name, kwargs in spy.calls if call_name == name]
        assert matching, f"tool {name!r} was never called; recorded={spy.calls!r}"
        assert any(
            all(kwargs.get(key) == value for key, value in expected_args.items())
            for kwargs in matching
        ), f"tool {name!r} args mismatch: expected {expected_args}, got {matching!r}"

    return check
