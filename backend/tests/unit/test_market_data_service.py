from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import cast

import pytest

from odrm.services.market_data import (
    MOCK_CARBON_CREDIT_PRICE_USD_PER_TONNE_CO2E,
    MOCK_NATURAL_GAS_PRICE_USD_PER_MMBTU,
    MOCK_SOURCE,
    MOCK_SYNGAS_PRICE_USD_PER_KMOL,
    MarketDataError,
    MarketDataService,
    MarketPriceQuote,
    MockMarketPriceProvider,
)


class StubProvider:
    def __init__(self, quote: MarketPriceQuote) -> None:
        self.quote = quote
        self.calls = 0

    def fetch(self) -> MarketPriceQuote:
        self.calls += 1
        return self.quote


class SlowProvider(StubProvider):
    def fetch(self) -> MarketPriceQuote:
        time.sleep(0.02)
        return super().fetch()


def make_quote(**overrides: object) -> MarketPriceQuote:
    values: dict[str, object] = {
        "natural_gas_price_usd_per_mmbtu": 3.25,
        "syngas_price_usd_per_kmol": 4.10,
        "carbon_credit_price_usd_per_tonne_co2e": 28.50,
        "as_of": datetime(2026, 11, 4, 12, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return MarketPriceQuote(**values)  # type: ignore[arg-type]


def test_get_prices_fetches_from_provider_on_first_call() -> None:
    quote = make_quote()
    provider = StubProvider(quote)
    service = MarketDataService(provider, ttl_seconds=60, clock=lambda: 100.0)

    result, cached = service.get_prices()

    assert result == quote
    assert cached is False
    assert provider.calls == 1


def test_get_prices_returns_cached_quote_within_ttl() -> None:
    quote = make_quote()
    provider = StubProvider(quote)
    now = [100.0]
    service = MarketDataService(provider, ttl_seconds=60, clock=lambda: now[0])

    first, first_cached = service.get_prices()
    now[0] = 159.0
    second, second_cached = service.get_prices()

    assert first == quote
    assert second == quote
    assert first_cached is False
    assert second_cached is True
    assert provider.calls == 1


def test_get_prices_refreshes_after_ttl_expires() -> None:
    quote = make_quote()
    provider = StubProvider(quote)
    now = [100.0]
    service = MarketDataService(provider, ttl_seconds=60, clock=lambda: now[0])

    service.get_prices()
    now[0] = 160.0
    _, cached = service.get_prices()

    assert cached is False
    assert provider.calls == 2


def test_zero_ttl_disables_caching() -> None:
    quote = make_quote()
    provider = StubProvider(quote)
    service = MarketDataService(provider, ttl_seconds=0, clock=lambda: 100.0)

    _, first_cached = service.get_prices()
    _, second_cached = service.get_prices()

    assert first_cached is False
    assert second_cached is False
    assert provider.calls == 2


def test_provider_failure_raises_market_data_error() -> None:
    class FailingProvider:
        def fetch(self) -> MarketPriceQuote:
            raise RuntimeError("provider exploded")

    service = MarketDataService(FailingProvider(), ttl_seconds=60, clock=lambda: 100.0)

    with pytest.raises(MarketDataError, match="provider exploded"):
        service.get_prices()


def test_invalid_provider_payload_raises_market_data_error() -> None:
    class BadProvider:
        def fetch(self) -> MarketPriceQuote:
            return cast(MarketPriceQuote, object())

    service = MarketDataService(BadProvider(), ttl_seconds=60, clock=lambda: 100.0)

    with pytest.raises(MarketDataError, match="invalid market quote"):
        service.get_prices()


def test_failed_refresh_does_not_replace_previous_quote() -> None:
    quote = make_quote()
    replacement = make_quote(natural_gas_price_usd_per_mmbtu=4.50)

    class SequencedProvider:
        def __init__(self) -> None:
            self.calls = 0

        def fetch(self) -> MarketPriceQuote:
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("temporary failure")
            return quote if self.calls == 1 else replacement

    provider = SequencedProvider()
    now = [100.0]
    service = MarketDataService(provider, ttl_seconds=10, clock=lambda: now[0])

    service.get_prices()
    now[0] = 111.0
    with pytest.raises(MarketDataError):
        service.get_prices()

    result, cached = service.get_prices()
    assert result == replacement
    assert cached is False
    assert provider.calls == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("natural_gas_price_usd_per_mmbtu", -0.01),
        ("natural_gas_price_usd_per_mmbtu", 1_000.01),
        ("syngas_price_usd_per_kmol", -1.0),
        ("syngas_price_usd_per_kmol", 1_000_000.01),
        ("carbon_credit_price_usd_per_tonne_co2e", -1.0),
        ("carbon_credit_price_usd_per_tonne_co2e", 100_000.01),
    ],
)
def test_quote_rejects_out_of_range_prices(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        make_quote(**{field: value})


def test_quote_requires_utc_as_of() -> None:
    with pytest.raises(ValueError, match="UTC"):
        make_quote(as_of=datetime(2026, 11, 4, 12, 0))


def test_mock_provider_uses_fixture_values_and_injected_clock() -> None:
    moment = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
    quote = MockMarketPriceProvider(clock=lambda: moment).fetch()

    assert quote.natural_gas_price_usd_per_mmbtu == MOCK_NATURAL_GAS_PRICE_USD_PER_MMBTU
    assert quote.syngas_price_usd_per_kmol == MOCK_SYNGAS_PRICE_USD_PER_KMOL
    assert quote.carbon_credit_price_usd_per_tonne_co2e == (
        MOCK_CARBON_CREDIT_PRICE_USD_PER_TONNE_CO2E
    )
    assert quote.as_of == moment
    assert quote.source == MOCK_SOURCE
    assert quote.is_mock is True


def test_service_rejects_negative_ttl() -> None:
    with pytest.raises(ValueError, match="ttl_seconds"):
        MarketDataService(StubProvider(make_quote()), ttl_seconds=-1)


def test_concurrent_misses_fetch_once() -> None:
    provider = SlowProvider(make_quote())
    service = MarketDataService(provider, ttl_seconds=60, clock=lambda: 100.0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result() for future in [pool.submit(service.get_prices) for _ in range(2)]
        ]

    assert provider.calls == 1
    assert [cached for _, cached in results] == [False, True]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("natural_gas_price_usd_per_mmbtu", float("nan")),
        ("syngas_price_usd_per_kmol", float("inf")),
        ("carbon_credit_price_usd_per_tonne_co2e", float("-inf")),
    ],
)
def test_quote_rejects_non_finite_prices(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        make_quote(**{field: value})


def test_quote_rejects_non_usd_currency() -> None:
    with pytest.raises(ValueError, match="USD"):
        make_quote(currency="EUR")
