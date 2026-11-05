# 🌍 Valoris: The AI Operating System for Flare Gas Valorization

**Turn wasted emissions into high-value chemicals.** 
*(Internal Engineering Codename: ODRM-Copilot)*

---

## 💡 The Problem: A Multi-Billion Dollar Waste
Every day, thousands of tons of natural gas are flared (burned off) at industrial sites and oil fields. This is a massive environmental hazard and a tragic waste of energy. Why does it happen? Because traditional methods of capturing and converting this gas into valuable chemicals require multi-million dollar infrastructure and proprietary simulation software that only a handful of PhDs can operate.

## 🚀 The Solution: The Valoris Platform - facilitating Waste to Wealth
**Valoris** is an AI-powered decision-support platform. We don't just predict chemical reactions; we tell operators if those reactions will make them money and reduce their carbon footprint.

You don't need a supercomputer or a chemical engineering degree. Just input your feed conditions, and our surrogate AI model tells you the optimal operating parameters to maximize profit and minimize carbon liability.

Here is how the platform works, from input to output:

1.  **User Input:** An operator inputs their chemical plant's conditions (feed composition, temperature, pressure) through a simple interface.
2.  **Agent Orchestrator:** Our intelligent system parses the request, validates the physics bounds (e.g., ensuring temperature doesn't exceed 1000°C), and routes the data.
3.  **Surrogate AI:** The system runs a highly optimized Machine Learning model (XGBoost) that predicts the chemical output in **milliseconds**—specifically CH4 conversion, H2/CO ratio, and Carbon Deposition Risk.
4.  **The TEA Engine:** This is our secret sauce. The Techno-Economic Analysis (TEA) engine takes the AI's chemical predictions and instantly calculates financial ROI based on real-time gas prices, operational costs, and carbon credit values.
5.  **The ESG Dashboard:** The operator receives a clear, actionable dashboard. It highlights the optimal operating parameters, warns of safety/carbon risks, and generates a downloadable ESG report for investors and regulators.

## 🌊 The Blue Ocean Strategy
We are not building physical reactors; we are building the software intelligence that makes them profitable. Hardware capture is becoming a commodity. Valoris is the **"Shovel and Picks"** software layer. By democratizing advanced simulation and financial modeling, we unlock a new market of mid-sized operators and emerging economies who have been priced out of the energy transition—until now. 
*(See [`COMMERCIAL_MODEL.md`](docs/strategy/COMMERCIAL_MODEL.md) for our full revenue strategy).*

## 🛠️ Under the Hood (For the Engineers)
*   **The Physics:** Powered by Oxy-Dry Reforming of Methane (ODRM) chemistry.
*   **The AI:** XGBoost surrogate models trained on thousands of thermodynamic simulations to provide **sub-50ms predictions**.
*   **The API:** A robust, versioned FastAPI backend (`/api/v1/predict`) designed to plug directly into existing plant control dashboards.

## 💻 Quick Start

**1. Navigate to the project directory and activate the environment:**
```powershell
cd odrm-copilot
```
**2. Install dependencies:**
```powershell
 .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
**3. Generate the synthetic dataset (Phase 1):**
```powershell
.\.venv\Scripts\python.exe scripts\generate_odrm_data.py --n 10000 --seed 7
```
**4. Run the test suite:**
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```
**5. Start the prediction API:**
```powershell
.\.venv\Scripts\python.exe -m uvicorn odrm.main:app --port 8000
```
**6. Test a prediction (requires `curl` or Postman):**
```powershell
curl -X POST http://localhost:8000/api/v1/predict `
     -H "Content-Type: application/json" `
     -d '{\"temperature_c\": 800.0, \"pressure_bar\": 10.0, \"ch4_o2_ratio\": 2.0, \"co2_ch4_ratio\": 0.5, \"h2o_ch4_ratio\": 0.2, \"ghsv_per_h\": 5000.0, \"catalyst\": \"Ni/Al2O3\"}'
```
*(Note: If you don't have `curl` on Windows, you can skip this or use PowerShell's `Invoke-RestMethod`).*

**7. Start the frontend dashboard:**
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:3000 in your browser to use the interactive screening dashboard.

## AI Screening Assistant

The dashboard includes an additive **Ask the Screening Assistant** section, backed by
`POST /api/v1/chat`. Send one plain-language screening request (maximum 2000 characters). The
backend extracts conditions and assumptions, validates them against the same physical and
financial bounds as `/api/v1/tea`, calls `/api/v1/tea` through the guarded tool, and returns the
authoritative `TeaResponse` in `result`. There is no conversation history, and the client cannot
override the provider, model, key, or endpoints.

### Configure a provider

The API starts without an LLM configured; `/chat` returns `503 AGENT_UNAVAILABLE` until a
provider is set. Use server-side environment variables only:

```text
# OpenAI
ODRM_LLM_PROVIDER=openai
ODRM_LLM_MODEL=<openai-model>
ODRM_LLM_API_KEY=<server-side-key>

# Local Ollama (OpenAI-compatible endpoint)
ODRM_LLM_PROVIDER=ollama
ODRM_LLM_MODEL=<installed-ollama-model>
ODRM_LLM_BASE_URL=http://localhost:11434/v1

# Gemini (OpenAI-compatible endpoint)
ODRM_LLM_PROVIDER=gemini
ODRM_LLM_MODEL=<gemini-model>
ODRM_LLM_API_KEY=<server-side-key>

# Internal TEA endpoint
ODRM_TEA_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Provider keys are never sent to the browser, written to logs, or included in errors.

### Example

```powershell
curl -X POST http://localhost:8000/api/v1/chat `
     -H "Content-Type: application/json" `
     -d '{"message": "At 750 C, 5 bar, CH4:O2 2.0, CO2:CH4 0.5, H2O:CH4 0.3, GHSV 20000/h, Ni/Al2O3, 10 wt%, 0% N2, with 100 kmol/h CH4 feed, $3.25/MMBtu gas, $4.10/kmol syngas, $28.50/tCO2e credits, and $5,000,000 capex. What is the conversion, yield, and payback?"}'
```

`status: "ok"` always includes a validated `result`; `status: "needs_input"` has `result: null`
and asks for the missing values. Guardrail failures return `422` with a structured `detail`
(`code`, `field`, `minimum`, `maximum`, `request_id`), while provider or TEA outages return
`503` with `AGENT_UNAVAILABLE` or `TEA_UNAVAILABLE`. This is a screening result, not investment
advice.



## 📊 Techno-Economic Analysis (TEA) API

The `/api/v1/tea` endpoint combines the surrogate AI predictions with a deterministic financial engine to screen the economic viability of a flare gas project.

**Important:** This is a screening tool, not an investment-grade financial model. It does not account for taxes, financing, inflation, or variable OPEX. Market prices are **never** fetched from the internet; the caller must supply them.

### Sample Request
```json
{
  "conditions": {
    "temperature_c": 800.0,
    "pressure_bar": 10.0,
    "ch4_o2_ratio": 2.0,
    "co2_ch4_ratio": 0.5,
    "h2o_ch4_ratio": 0.2,
    "ghsv_per_h": 5000.0,
    "catalyst": "Ni/Al2O3"
  },
  "assumptions": {
    "ch4_feed_kmol_per_h": 100.0,
    "natural_gas_price_usd_per_mmbtu": 3.0,
    "syngas_price_usd_per_kmol": 4.0,
    "carbon_credit_price_usd_per_tonne_co2e": 25.0,
    "co2_utilization_fraction": 0.4,
    "capex_usd": 5000000.0
  }
}
```

### Engineering Defaults
If omitted, the engine assumes:
*   `operating_hours_per_day`: 24.0
*   `operating_days_per_year`: 330.0
*   `opex_pct_of_capex_per_year`: 5.0
*   `co2_utilization_fraction`: 0.0 (Conservative: no carbon credit is assumed unless specified).

### Important Formulas & Basis
*   **Syngas Yield:** Calculated as mol syngas per mol CH4 **fed**, not per mol converted.
*   **Carbon Credits:** Based on CO2 utilization (`ch4_feed × co2_ch4_ratio × co2_utilization_fraction`). If utilization is 0, a warning `carbon_credit_not_included` is returned.
*   **Negative Cash Flow:** If annual cash flow is negative, the ROI will be negative and `payback_years` will be `null`.

---

## 🌱 The Impact
*   **For the Operator:** Turn a wasted liability into a revenue-generating chemical asset.
*   **For the ESG Investor:** A measurable, scalable path to reducing Scope 1 emissions.
*   **For the Climate:** A transition from flaring to a circular carbon economy.

## 📄 License

The synthetic data generator, schema validator, and developer tooling in this repository are open-source under the [MIT License](LICENSE). 

The trained ML surrogate models and the production `/api/v1/predict` SaaS dashboard endpoints are proprietary and subject to Valoris commercial terms.

## 📊 Techno-Economic Analysis (TEA) API

The `/api/v1/tea` endpoint combines the surrogate AI predictions with a deterministic financial engine to screen the economic viability of a flare gas project.

**Important:** This is a screening tool, not an investment-grade financial model. It does not account for taxes, financing, inflation, or variable OPEX. Market prices are **never** fetched from the internet; the caller must supply them.

### Sample Request
```json
{
  "conditions": {
    "temperature_c": 800.0,
    "pressure_bar": 10.0,
    "ch4_o2_ratio": 2.0,
    "co2_ch4_ratio": 0.5,
    "h2o_ch4_ratio": 0.2,
    "ghsv_per_h": 5000.0,
    "catalyst": "Ni/Al2O3"
  },
  "assumptions": {
    "ch4_feed_kmol_per_h": 100.0,
    "natural_gas_price_usd_per_mmbtu": 3.0,
    "syngas_price_usd_per_kmol": 4.0,
    "carbon_credit_price_usd_per_tonne_co2e": 25.0,
    "co2_utilization_fraction": 0.4,
    "capex_usd": 5000000.0
  }
}
```
