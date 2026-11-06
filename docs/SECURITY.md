# ODRM-Copilot: Master Roadmap & Commercial Strategy

## PART 1: CTO Architectural Blueprint

**Product Name:** ODRM-Copilot (Internal Codename: *Syngas Shovel*)
**Core Value Proposition:** A B2B SaaS platform that uses Surrogate AI and Agentic workflows to predict, optimize, and financially model Oxy-Dry Reforming of Methane (ODRM). It bypasses the need for $50k/year simulation software licenses and years of specialized training, democratizing process engineering for the Global South.

### 1. The Tech Stack
*   **Frontend:** Next.js (React), Tailwind CSS, Recharts/Plotly (for interactive thermodynamics curves), Vercel (Hosting).
*   **Backend API:** FastAPI (Python).
*   **Data Layer:** PostgreSQL (User profiles, project data), Redis (Caching ML predictions), Parquet (Storing ODRM datasets).
*   **Machine Learning (The Surrogate):** PyTorch or XGBoost. A multi-layer perceptron (MLP) or gradient boosting model acts as a fast surrogate for COMSOL/Aspen physics models.
*   **Agentic Layer:** LangChain or DSPy. An LLM translates natural language into structured tool calls (ML inference, TEA calculator).
*   **The Evidence Chain:** A Merkle-tree based logging system that hashes every prediction, input parameter, and model version used, generating immutable ESG/Carbon reports.

### 2. System Flow
1.  **User Input:** Natural language or form input (Feed composition, Temp, Pressure).
2.  **Agent Orchestrator:** Parses intent, validates physics bounds (e.g., Temp < 1000°C).
3.  **Surrogate Model:** Runs inference in <50ms (predicting CH4 Conversion, H2/CO ratio, Carbon Deposition Risk).
4.  **TEA Engine:** Calculates the financial ROI based on current gas prices and carbon credit values (via the Market Data Service).
5.  **Output:** A dashboard with the optimal operating parameters, risk warnings, and an ESG report.

---

## PART 2: PMBOK Governance & Commercial Model

**Blue Ocean Strategy (Shovel-and-Picks):**
We sell the "picks" (software optimization) to the "miners" (plant operators, university researchers, local gas processors). We do not own the physical reactors; we own the intelligence that makes their reactors profitable and safe. The product is the "Digital Twin" and the intelligence layer.

### Risk Register (Probability-Impact)
| Risk ID | Risk Description | Prob | Impact | Score | Mitigation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-001** | Data Scarcity (No real simulator data) | 3 | 4 | 12 | Use open-source thermodynamics (Cantera/DWSIM) or the Kahobe thesis data to bootstrap. |
| **R-002** | Agent Hallucination | 2 | 5 | 10 | Hard-coded physics guardrails. The LLM cannot pass data to the ML model unless it fits a strict schema. |
| **R-003** | User Trust (Engineers don't trust AI) | 4 | 3 | 12 | Show the "Evidence Chain." Allow users to see the underlying physics data points and confidence intervals. |

---

## PART 3: Sprint Execution Roadmap (Sprint 1 to Sprint 9)

*All sprints strictly follow the 5-Phase workflow defined in `docs/SPRINT_WORKFLOW.md`: Constitution → Plan-First → Review Gate → Implementation → Report.*

### 🟢 Sprint 1: Data Engineering (The Foundation)
**Goal:** Generate the dataset that the AI will learn from.
**Deliverables:**
1. A Python script (`scripts/generate_odrm_data.py`) that uses the thermodynamic equations from Frank Kahobe's thesis to mock ODRM reactions.
2. A dataset of 10,000 records (`data/odrm_dataset.parquet`).
3. A strict validator (`backend/src/odrm/data/schema.py`) enforcing physics bounds (e.g., Temp < 1000°C).

### 🟢 Sprint 2: Surrogate ML Model (The Brain)
**Goal:** Train an ML model that replaces slow physics simulation.
**Deliverables:**
1. An XGBoost model (`src/models/train_surrogate.py`) trained on the Sprint 1 dataset.
2. Validation metrics enforcing an R² score > 0.95.
3. A FastAPI route `/api/predict` that accepts JSON and returns the ML prediction.

### 🟢 Sprint 3: TEA Engine (The Money)
**Goal:** Turn the AI predictions into actionable financial ROI.
**Deliverables:**
1. A pure, deterministic financial engine (`backend/src/odrm/domain/tea.py`) that calculates daily revenue, OPEX, carbon credits, and ROI.
2. A new FastAPI route `POST /api/v1/tea` that takes plant conditions and financial assumptions.
3. Tests ensuring the math is strictly auditable and requires no network calls.

### 🟢 Sprint 4: Core UI/UX, Market Data & Evidence Chain
**Goal:** A beautiful frontend that engineers can trust, fed by live market prices.
**Deliverables:**
1. A Next.js dashboard with an input form (Feed Composition, Temp).
2. A results panel showing predicted H2/CO ratio and Carbon risk.
3. **Market Data Service:** Implement `GET /api/v1/market-prices` to fetch live gas and carbon credit prices for the TEA engine, with caching to prevent API rate limits.
4. The **Evidence Chain Component**: A UI list showing the model version used and the confidence score of the prediction.

### 🟢 Sprint 5: Agentic Orchestrator (The Interface)
**Goal:** Allow users to ask questions in plain English.
**Deliverables:**
1. A LangChain agent (`src/agent/orchestrator.py`) initialized with a strict system prompt.
2. A tool called `calculate_project_economics()` wired to the FastAPI endpoints.
3. Tests ensuring the agent extracts parameters correctly and does not hallucinate physics.

### 🟢 Sprint 6: The ESG Export Engine (Automated Compliance)
**Goal:** Fulfill the pitch deck promise of automated compliance reporting.
**Deliverables:**
1. A new backend endpoint `POST /api/v1/report` that generates a professional PDF.
2. The PDF will contain plant conditions, AI predictions, financial ROI, and a compliance timestamp.
3. A "Download ESG Report" button on the frontend Results Panel.

### 🟢 Sprint 7: Beta Launch & Hardening (The Production Layer)
**Goal:** Secure the platform and prepare it for real users.
**Deliverables:**
1. User Authentication (JWT) so operators have private logins.
2. API Rate Limiting to prevent abuse.
3. Docker Compose setup for easy deployment.
4. `docs/API_DOCUMENTATION.md` and `docs/USER_GUIDE.md`.

### 🟡 Sprint 8: Real-World Pilot Integration (Blocked pending NUPRC Data)
**Goal:** Make the product usable for real-world, dirty gas.
**Deliverables:**
1. Update the dataset and model to handle impurities (H2S, N2) and variable feedstocks (Landfill gas vs. Flare gas).
2. Add a "Predictive Maintenance" output in the UI: If Carbon Risk is >80%, flash a warning to adjust O2 flow.
3. Train the models on historical data from at least one, and at most three of the 28 flare gas sites (via the NUPRC pilot).
4. **Security Hardening:** Implement Role-Based Access Control (RBAC), Refresh Tokens, and a strict Content Security Policy (CSP).
5. **UI "Coming Soon" Banner:** Add a visually distinct panel to the dashboard showcasing the upcoming features to drive pilot adoption.

### 🟡 Sprint 9: Cryptographic ESG & Carbon Accounting (Blocked pending Pilot)
**Goal:** Provide the immutable audit trail for carbon credits.
**Deliverables:**
1. Implement a cryptographic hash chain (Merkle tree) for every successful prediction.
2. Endpoint `/api/export_esg_report` that generates a PDF containing user inputs, AI recommendation, CO2 consumed, and the cryptographic hash proving no tampering.
3. **Security Hardening:** Implement Redis-backed JWT revocation and Multi-Factor Authentication (MFA) for admins.
4. **UI "Coming Soon" Banner:** Update the banner to show the status of the Merkle-tree evidence chain.