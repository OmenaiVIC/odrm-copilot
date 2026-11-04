# Valoris Market Data Service (Future Backlog)

## The Problem
The TEA (Techno-Economic Analysis) engine built in Sprint 3 is deliberately pure, deterministic, and offline. It requires the caller to supply prices for natural gas, syngas, and carbon credits. 
However, a commercial SaaS platform cannot expect users to manually type in today's carbon credit price every time they run a simulation. We need a way to fetch live market data.

## The Solution: The Market Data Service
We will build a separate service layer (`backend/src/odrm/services/market_data.py`) that acts as the bridge between the outside world and the pure TEA engine.

1. **External APIs:** The service will connect to public or paid APIs for:
   - Nigerian Natural Gas prices (USD/MMBtu)
   - Global Carbon Credit prices (USD/tonne CO2e)
   - Syngas / Methanol spot prices (USD/tonne)

2. **Caching:** To prevent rate-limiting and reduce costs, the service will cache these prices in memory or a database for a set period (e.g., 24 hours).

3. **The UI Flow:**
   - When a user opens the dashboard, the UI calls `GET /api/v1/market-prices`.
   - The Market Data Service fetches the latest numbers (or returns the cache).
   - The user can *override* these numbers in the UI if they have a specific local contract price.
   - The UI passes the final numbers into the `POST /api/v1/tea` endpoint.

## Why this architecture?
By keeping the Market Data Service separate from the TEA Engine, we ensure that the core financial math remains auditable and reproducible. If an API goes down, the TEA engine still works perfectly as long as the user manually inputs the numbers.

## Target Sprint
This should be implemented in the sprint that builds the Frontend UI/Dashboard (Sprint 4 or 5), right before we pitch to the general public.