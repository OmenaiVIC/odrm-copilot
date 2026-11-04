from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from odrm.core.config import Settings
from odrm.main import create_app
from odrm.services.market_data import (
    MarketDataError,
    MarketDataService,
    MarketPriceProvider,
    MarketPriceQuote,
)

pytestmark = pytest.mark.unit

EXPECTED_FIELDS = {
    "natural_gas_price_usd_per_mmbtu",
    "syngas_price_usd_per_kmol",
    "carbon_credit_price_usd_per_tonne_co2e",
    "currency",
    "source",
    "is_mock",
    "as_of",
    "cached",
    "cache_ttl_seconds",
}


@pytest.fixture()
def market_client(test_settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings=test_settings)
    with TestClient(app) as client:
        yield client


def test_market_prices_endpoint_returns_fresh_quote_then_cache_hit(
    market_client: TestClient,
) -> None:
    first = market_client.get("/api/v1/market-prices")

    assert first.status_code == 200
    data = first.json()
    assert set(data) == EXPECTED_FIELDS
    assert data["natural_gas_price_usd_per_mmbtu"] == pytest.approx(3.25)
    assert data["syngas_price_usd_per_kmol"] == pytest.approx(4.10)
    assert data["carbon_credit_price_usd_per_tonne_co2e"] == pytest.approx(28.50)
    assert data["currency"] == "USD"
    assert data["source"] == "mock-fixture-v1"
    assert data["is_mock"] is True
    assert data["cached"] is False
    assert data["cache_ttl_seconds"] == 86_400

    as_of = datetime.fromisoformat(data["as_of"].replace("Z", "+00:00"))
    assert as_of.utcoffset() == timedelta(0)

    second = market_client.get("/api/v1/market-prices")

    assert second.status_code == 200
    cached = second.json()
    assert cached["cached"] is True
    assert cached["as_of"] == data["as_of"]
    assert cached["cache_ttl_seconds"] == 86_400


def test_market_prices_endpoint_echoes_configured_ttl(test_settings: Settings) -> None:
    settings = test_settings.model_copy(update={"market_data_ttl_seconds": 0})
    app = create_app(settings=settings)

    with TestClient(app) as client:
        first = client.get("/api/v1/market-prices")
        second = client.get("/api/v1/market-prices")

    assert first.status_code == 200
    assert first.json()["cache_ttl_seconds"] == 0
    assert first.json()["cached"] is False
    assert second.json()["cached"] is False


def test_market_prices_endpoint_returns_generic_503_on_provider_failure(
    market_client: TestClient,
) -> None:
    class FailingProvider:
        def fetch(self) -> MarketPriceQuote:
            raise MarketDataError("secret upstream detail")

    cast(Any, market_client.app).state.market_data = MarketDataService(
        FailingProvider(), ttl_seconds=60
    )

    response = market_client.get("/api/v1/market-prices")

    assert response.status_code == 503
    assert response.json() == {"detail": "Market data unavailable."}
    assert "secret upstream detail" not in response.text


def test_market_prices_endpoint_returns_generic_503_on_malformed_quote(
    market_client: TestClient,
) -> None:
    class MalformedProvider:
        def fetch(self) -> MarketPriceQuote:
            return cast(MarketPriceQuote, object())

    cast(Any, market_client.app).state.market_data = MarketDataService(
        MalformedProvider(), ttl_seconds=60
    )

    response = market_client.get("/api/v1/market-prices")

    assert response.status_code == 503
    assert response.json() == {"detail": "Market data unavailable."}


def test_app_exposes_market_data_service(client: TestClient) -> None:
    service = cast(MarketPriceProvider, client.app.state.market_data)
    assert isinstance(service, MarketDataService)


@pytest.mark.parametrize("ttl", [-1, 604_801])
def test_settings_rejects_out_of_range_market_ttl(ttl: int) -> None:
    with pytest.raises(ValidationError):
        Settings(market_data_ttl_seconds=ttl)
