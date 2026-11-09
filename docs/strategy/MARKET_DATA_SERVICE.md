# Valoris Market Data Service (Architecture)

**Status:** Live (Implemented in Sprint 4)

## The Problem
The TEA (Techno-Economic Analysis) engine built in Sprint 3 is deliberately pure, deterministic, and offline. It requires the caller to supply prices for natural gas, syngas, and carbon credits. 
However, a commercial SaaS platform cannot expect users to manually type in today's carbon credit price every time they run a simulation. We need a way to fetch live market data.

## The Solution: The Market Data Service
We built a separate service layer (`backend/src/odrm/services/market_data.py`) that acts as the bridge between the outside world and the pure TEA engine.

1. **Mock Provider (Current):** The service currently returns a realistic mock quote to prove the pipeline. 
2. **Caching:** To prevent rate-limiting and reduce costs, the service caches prices in memory for a set period (24 hours).
3. **The UI Flow:**
   - When a user opens the dashboard, the UI calls `GET /api/v1/market-prices`.
   - The Market Data Service fetches the latest numbers (or returns the cache).
   - The user can *override* these numbers in the UI if they have a specific local contract price.
   - The UI passes the final numbers into the `POST /api/v1/tea` endpoint.

## Future Integration (Phase 2)
In the future, the `MockMarketPriceProvider` will be swapped for a `LiveMarketPriceProvider` that connects to public or paid APIs for:
   - Nigerian Natural Gas prices (USD/MMBtu)
   - Global Carbon Credit prices (USD/tonne CO2e)

## Why this architecture?
By keeping the Market Data Service separate from the TEA Engine, we ensure that the core financial math remains auditable and reproducible. If an API goes down, the TEA engine still works perfectly as long as the user manually inputs the numbers.