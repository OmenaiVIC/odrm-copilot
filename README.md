# 🌍 Valoris: The AI Operating System for Flare Gas Valorization

**Turn wasted emissions into high-value chemicals.** 
*(Internal Engineering Codename: ODRM-Copilot)*

---

## 💡 The Problem: A Multi-Billion Dollar Waste
Every day, thousands of tons of natural gas are flared (burned off) at industrial sites and oil fields across the Global South. This is a massive environmental hazard and a tragic waste of energy. Why does it happen? Because traditional methods of capturing and converting this gas into valuable chemicals require multi-million dollar infrastructure and proprietary simulation software (like Aspen HYSYS) that only a handful of PhDs can operate. Without this "economic proof," capital is never deployed, and projects stall.

## 🚀 The Solution: The Action Layer for Flare Gas
**Valoris** is an AI-powered decision-support platform. We don't just predict chemical reactions; we tell operators if those reactions will make them money and reduce their carbon footprint.

Here is exactly how the platform works, from input to output:

1.  **User Input:** An operator inputs their plant's conditions (feed composition, temperature, pressure, capex) through a simple web interface or conversational AI.
2.  **Agent Orchestrator:** Our intelligent system parses the request, validates the physics bounds (e.g., ensuring temperature doesn't exceed 1000°C), and routes the data.
3.  **Surrogate AI:** The system runs a highly optimized Machine Learning model (XGBoost) that predicts the chemical output in **milliseconds**—specifically CH4 conversion and Syngas yield.
4.  **The TEA Engine:** The Techno-Economic Analysis (TEA) engine takes the AI's chemical predictions and instantly calculates financial ROI and payback period based on the gas prices, operational costs, and carbon credit values supplied by the operator.
5.  **The ESG Dashboard:** The operator receives a clear, actionable dashboard. It highlights the optimal operating parameters, flags economic risks, and generates a downloadable, cryptographically hashed ESG report for investors and regulators.

### 🤝 Flagship Synergy: NOGIET & NUPRC
While Valoris is a globally applicable SaaS platform for emerging markets, our flagship partnership is with the Nigerian Upstream Petroleum Regulatory Commission (NUPRC). 
*   **NOGIET (The Eyes):** Detects methane plumes via satellite.
*   **Valoris (The Hands):** Proves the economic solution. 

By integrating with NOGIET, Valoris closes the gap between detection and remediation. We turn a regulatory warning into a profitable business case for the 28 NGFCP permit holders.

## 🌊 The Commercial Strategy (Global SaaS + National Pilots)
We are not building physical reactors; we are building the software intelligence that makes them profitable. Hardware capture is becoming a commodity. 

Valoris is the **"Shovel and Picks"** software layer. Our 3-phase go-to-market strategy is:

1.  **The Pilot (e.g., NUPRC):** Partner with national regulators to train our AI on anonymized historical data, proving the system's accuracy on real-world "dirty gas."
2.  **The Operator Subscription (Global):** Mid-sized operators pay a monthly SaaS fee to access the dashboard, calculate ROI, and automatically generate ESG compliance reports.
3.  **The Regulatory Dashboard (Government):** Regulators receive high-level access for free to monitor national progress and attract international ESG investment.

## 🛠️ Under the Hood (For the Engineers)
Valoris is a production-grade, Dockerized, full-stack application built to be regulatory-agnostic.

*   **The Physics:** Powered by Oxy-Dry Reforming of Methane (ODRM) chemistry.
*   **The AI:** XGBoost surrogate models trained on 10,000 thermodynamic scenarios, achieving >98% accuracy. Predictions are served in **sub-50ms**.
*   **The Agent:** A LangChain agentic orchestrator (Google Gemini) that parses natural language, validates physics bounds, and calls the TEA engine. It features **multi-turn memory**, allowing users to ask follow-up questions.
*   **The API:** A robust, versioned FastAPI backend (`/api/v1/predict`, `/api/v1/tea`, `/api/v1/chat`).
*   **The Backend:** PostgreSQL, JWT Authentication, and Rate Limiting. Deployed via Docker Compose.
*   **The Frontend:** Next.js 16 (React 19, Tailwind v4) with TanStack Query and React-Markdown for a modern, responsive UI.

---

## 💻 Quick Start (Dockerized)

The fastest way to run the full stack (Database, API, and UI) is using Docker.

**1. Create your Docker environment file:**
```powershell  
copy .env.docker.example .env.docker
```
(Edit .env.docker and insert your Gemini API key: ODRM_LLM_API_KEY=...)

**2. Build and start the containers:**
```powershell
docker compose --env-file .env.docker up --build -d
```
This will boot the PostgreSQL database, the FastAPI backend (running Alembic migrations), and the Next.js frontend.

**3. Create your Admin User:**
```powershell
docker compose --env-file .env.docker exec api python -m odrm.cli create-user --email admin@example.com
```
**4. Access the Dashboard:**
Open `http://localhost:3000` in your browser and log in with the credentials you just created.


### Option B: Local Python (For Developers)
If you prefer to run the backend locally without Docker:

**1. Navigate and install dependencies:**
```powershell
cd odrm-copilot
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
**2. Generate the synthetic dataset:**
```powershell
.\.venv\Scripts\python.exe scripts\generate_odrm_data.py --n 10000 --seed 7
```
**3. Run the test suite:**
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```
**4. Start the prediction API:**
```powershell
.\.venv\Scripts\python.exe -m uvicorn odrm.main:app --port 8000
```
**5. Start the frontend dashboard (in a new terminal):**
```powershell
cd frontend
npm install
npm run dev
```

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

## 🤖 AI Screening Assistant (Multi-Turn Memory)
The dashboard includes a conversational AI assistant backed by POST /api/v1/chat. You can ask it to run a screening in plain English, and it will extract the variables, validate the physics, call the TEA engine, and return a complete financial report.

Multi-Turn Memory: The assistant remembers the context of your conversation. If you ask a follow-up question (e.g., "What if we drop the CAPEX to $3M?"), it will use the previously provided conditions to recalculate the result without you having to repeat yourself.

Example Prompt:

"I have a plant running at 800C, 10 bar. The feed ratios are CH4:O2 2.0, CO2:CH4 0.5, and H2O:CH4 0.2. The GHSV is 5000/h and the catalyst is Ni/Al2O3. The feed rate is 100 kmol/h. Natural gas is $3.25/MMBtu, syngas is $4.10/kmol, and carbon credits are $28.50/tonne. CAPEX is 5 million. Can you calculate the ROI and payback period?"

## Configure the AI Provider
To enable the chat feature, configure your .env file:

```text
# For local Ollama (free)
ODRM_LLM_PROVIDER=ollama
ODRM_LLM_MODEL=qwen-odrm
ODRM_LLM_BASE_URL=http://localhost:11434/v1

# Or for Gemini
# ODRM_LLM_PROVIDER=gemini
# ODRM_LLM_MODEL=gemini-2.5-flash
# ODRM_LLM_API_KEY=your_api_key_here
```

## 🌱 The Impact
*   **For the Operator:** Turn a wasted liability into a revenue-generating chemical asset.
*   **For the ESG Investor:** A measurable, scalable path to reducing Scope 1 emissions.
*   **For the Climate:** A transition from flaring to a circular carbon economy.

## 🗺️ Roadmap
*   **[x] Sprints 1-8:** Data Engineering, ML Surrogate, TEA Engine, UI/Market Data, Agentic Orchestrator (with Multi-Turn Memory), ESG Export, and Dockerized Beta Hardening.
*   **[ ] Sprint 9 (Pilot):** Integration with satellite tracking APIs (NOGIET) and Predictive Maintenance.
*   **[ ] Sprint 10 (Pilot):** **Cryptographic Carbon Credits & Tokenization.** Implementation of a Merkle-tree audit trail and on-chain verification (smart contracts) to make carbon credits fully bankable and tradeable by international ESG investors.

## 📄 License

The synthetic data generator, schema validator, and developer tooling in this repository are open-source under the [MIT License](LICENSE). 

The trained ML surrogate models and the production `/api/v1/predict` SaaS dashboard endpoints are proprietary and subject to Valoris commercial terms.















