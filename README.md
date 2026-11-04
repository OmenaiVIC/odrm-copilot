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

*(Note: If you don't have `curl` on Windows, you can skip this or use PowerShell's `Invoke-RestMethod`).*

## TEA API (Screening Economics)

`POST /api/v1/tea` combines the existing surrogate predictions with a deterministic
techno-economic screen: syngas production and revenue, CO2 consumption and carbon
credit value, operating cash flow, ROI, and payback.

The endpoint is a **screening estimate, not investment-grade advice**. It excludes
tax, financing, depreciation, maintenance escalation, and discounted cash-flow
analysis. Carbon credits are an engineering estimate based on the supplied
utilization fraction; they are not a verified credit or an ESG eligibility claim.

### Assumptions

Gas, syngas, and carbon prices are **required**. The backend never fetches market
data and has no positive price defaults.

| Field | Default | Meaning |
|---|---:|---|
| `ch4_feed_kmol_per_h` | required | Methane feed rate; GHSV alone does not determine reactor volume |
| `natural_gas_price_usd_per_mmbtu` | required | Feed gas price |
| `syngas_price_usd_per_kmol` | required | Blended syngas price |
| `carbon_credit_price_usd_per_tonne_co2e` | required | Carbon credit price |
| `capex_usd` | required | Installed capital cost |
| `co2_utilization_fraction` | `0.0` | Share of stoichiometric CO2 consumption credited; warning when omitted |
| `opex_pct_of_capex_per_year` | `5.0` | Annual OPEX as a percentage of CAPEX |
| `operating_hours_per_day` | `24.0` | Operating hours per day |
| `operating_days_per_year` | `330.0` | Operating days per year |

`syngas_yield_mol_per_mol_ch4` is predicted per mole of CH4 **fed**, not per mole
converted. A non-positive annual cash flow returns `payback_years: null` and a
`negative_annual_cash_flow` warning. Warnings are always present and may be empty.

### Example

```powershell
curl -X POST http://localhost:8000/api/v1/tea `
     -H "Content-Type: application/json" `
     -d '{"conditions":{"temperature_c":800.0,"pressure_bar":10.0,"ch4_o2_ratio":2.0,"co2_ch4_ratio":0.5,"h2o_ch4_ratio":0.2,"ghsv_per_h":5000.0,"catalyst":"Ni/Al2O3"},"assumptions":{"ch4_feed_kmol_per_h":100.0,"natural_gas_price_usd_per_mmbtu":3.0,"syngas_price_usd_per_kmol":4.0,"carbon_credit_price_usd_per_tonne_co2e":25.0,"co2_utilization_fraction":0.4,"capex_usd":5000000.0}}'
```

The response contains `predictions`, `model_versions`, `financials`, and `warnings`.
`/api/v1/predict` is unchanged and remains the prediction-only endpoint.

Validation failures return `422`; missing models return `503`; non-finite model
output or a non-finite TEA result returns `500` without a stack trace or partial
financials.

---

## 🌱 The Impact
*   **For the Operator:** Turn a wasted liability into a revenue-generating chemical asset.
*   **For the ESG Investor:** A measurable, scalable path to reducing Scope 1 emissions.
*   **For the Climate:** A transition from flaring to a circular carbon economy.

## 📄 License

The synthetic data generator, schema validator, and developer tooling in this repository are open-source under the [MIT License](LICENSE). 

The trained ML surrogate models and the production `/api/v1/predict` SaaS dashboard endpoints are proprietary and subject to Valoris commercial terms.





The trained ML surrogate models, the TEA Engine, and the production SaaS dashboard endpoints are proprietary and subject to Valoris commercial terms.








