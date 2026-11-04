from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

MAX_NATURAL_GAS_PRICE_USD_PER_MMBTU = 1_000.0
MAX_SYNGAS_PRICE_USD_PER_KMOL = 1_000_000.0
MAX_CARBON_CREDIT_PRICE_USD_PER_TONNE_CO2E = 100_000.0
MOCK_SOURCE = "mock-fixture-v1"
MOCK_NATURAL_GAS_PRICE_USD_PER_MMBTU = 3.25
MOCK_SYNGAS_PRICE_USD_PER_KMOL = 4.10
MOCK_CARBON_CREDIT_PRICE_USD_PER_TONNE_CO2E = 28.50


class MarketDataError(RuntimeError):
    """Raised when market prices cannot be fetched or validated."""


@dataclass(frozen=True, slots=True)
class MarketPriceQuote:
    natural_gas_price_usd_per_mmbtu: float
    syngas_price_usd_per_kmol: float
    carbon_credit_price_usd_per_tonne_co2e: float
    as_of: datetime
    currency: str = "USD"
    source: str = MOCK_SOURCE
    is_mock: bool = True

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise ValueError("currency must be USD")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() != timedelta(0):
            raise ValueError("as_of must be a timezone-aware UTC datetime")
        if not self.source:
            raise ValueError("source must not be empty")
        _validate_price(
            "natural_gas_price_usd_per_mmbtu",
            self.natural_gas_price_usd_per_mmbtu,
            MAX_NATURAL_GAS_PRICE_USD_PER_MMBTU,
        )
        _validate_price(
            "syngas_price_usd_per_kmol",
            self.syngas_price_usd_per_kmol,
            MAX_SYNGAS_PRICE_USD_PER_KMOL,
        )
        _validate_price(
            "carbon_credit_price_usd_per_tonne_co2e",
            self.carbon_credit_price_usd_per_tonne_co2e,
            MAX_CARBON_CREDIT_PRICE_USD_PER_TONNE_CO2E,
        )


def _validate_price(name: str, value: float, maximum: float) -> None:
    if not math.isfinite(value) or value < 0.0 or value > maximum:
        raise ValueError(f"{name} must be finite and between 0 and {maximum}")


class MarketPriceProvider(Protocol):
    def fetch(self) -> MarketPriceQuote: ...


class MockMarketPriceProvider:
    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch(self) -> MarketPriceQuote:
        return MarketPriceQuote(
            natural_gas_price_usd_per_mmbtu=MOCK_NATURAL_GAS_PRICE_USD_PER_MMBTU,
            syngas_price_usd_per_kmol=MOCK_SYNGAS_PRICE_USD_PER_KMOL,
            carbon_credit_price_usd_per_tonne_co2e=MOCK_CARBON_CREDIT_PRICE_USD_PER_TONNE_CO2E,
            as_of=self._clock(),
        )


class MarketDataService:
    def __init__(
        self,
        provider: MarketPriceProvider,
        ttl_seconds: float = 86_400,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be non-negative")
        self._provider = provider
        self._ttl_seconds = ttl_seconds
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._cached_quote: MarketPriceQuote | None = None
        self._cached_at: float | None = None

    @property
    def ttl_seconds(self) -> float:
        return self._ttl_seconds

    def get_prices(self) -> tuple[MarketPriceQuote, bool]:
        with self._lock:
            now = self._clock()
            if self._is_cache_valid(now):
                return self._cached_quote, True  # type: ignore[return-value]

            try:
                quote = self._provider.fetch()
            except MarketDataError:
                raise
            except Exception as exc:
                raise MarketDataError(f"market data provider failed: {exc}") from exc

            if not isinstance(quote, MarketPriceQuote):
                raise MarketDataError("market data provider returned an invalid market quote")

            self._cached_quote = quote
            self._cached_at = now
            return quote, False

    def _is_cache_valid(self, now: float) -> bool:
        return (
            self._ttl_seconds > 0
            and self._cached_quote is not None
            and self._cached_at is not None
            and now - self._cached_at < self._ttl_seconds
        )
