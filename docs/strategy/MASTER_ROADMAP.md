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
4.  **TEA Engine:** Calculates the financial ROI based on current gas prices and carbon credit values.
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

## PART 3: Sprint Execution Roadmap (Sprint 1 to Sprint 8)

*All sprints strictly follow the 5-Phase workflow defined in `docs/SPRINT_WORKFLOW.md`: Constitution → Plan-First → Review Gate → Implementation → Report.*

### 🟢 Sprint 1: Data Engineering (The Foundation)
**Goal:** Generate the dataset that the AI will learn from.
**Deliverables:**
1.  A Python script (`scripts/generate_odrm_data.py`) that uses the thermodynamic equations from Frank Kahobe's thesis to mock ODRM reactions.
2.  A dataset of 10,000 records (`data/odrm_dataset.parquet`).
3.  A strict validator (`backend/src/odrm/data/schema.py`) enforcing physics bounds (e.g., Temp < 1000°C).

### 🟢 Sprint 2: Surrogate ML Model (The Brain)
**Goal:** Train an ML model that replaces slow physics simulation.
**Deliverables:**
1.  An XGBoost model (`src/models/train_surrogate.py`) trained on the Sprint 1 dataset.
2.  Validation metrics enforcing an R² score > 0.95.
3.  A FastAPI route `/api/predict` that accepts JSON and returns the ML prediction. 

### 🟢 Sprint 3: Agentic Orchestrator (The Interface)
**Goal:** Allow users to ask questions in plain English.
**Deliverables:**
1.  A LangChain agent (`src/agent/orchestrator.py`) initialized with a strict system prompt.
2.  A tool called `predict_odrm_conditions()` wired to the FastAPI endpoint.
3.  Tests ensuring the agent extracts parameters correctly and does not hallucinate physics.

### 🟢 Sprint 4: Core UI/UX & Evidence Chain
**Goal:** A beautiful frontend that engineers can trust.
**Deliverables:**
1.  A Next.js dashboard with an input form (Feed Composition, Temp).
2.  A results panel showing predicted H2/CO ratio and Carbon risk.
3.  The **Evidence Chain Component**: A UI list showing the model version used and the confidence score of the prediction.

### 🟢 Sprint 5: Techno-Economic Analysis (TEA) Module
**Goal:** Show the plant operator the money.
**Deliverables:**
1.  Extend the ML model/backend to include a TEA calculator (Estimated ROI based on inputted gas costs and carbon credit values).
2.  UI panels showing "Estimated Profit: $X/ton" and "Carbon Credits Generated: Y".

### 🟢 Sprint 6: Expanded Feedstocks & Predictive Maintenance
**Goal:** Make the product usable for real-world, dirty gas.
**Deliverables:**
1.  Update the dataset and model to handle impurities (H2S, N2) and variable feedstocks (Landfill gas vs. Flare gas).
2.  Add a "Predictive Maintenance" output in the UI: If Carbon Risk is >80%, flash a warning to adjust O2 flow.

### 🟢 Sprint 7: ESG & Carbon Accounting
**Goal:** Provide the immutable audit trail for carbon credits.
**Deliverables:**
1.  Implement a cryptographic hash chain (Merkle tree) for every successful prediction.
2.  Endpoint `/api/export_esg_report` that generates a PDF containing user inputs, AI recommendation, CO2 consumed, and the cryptographic hash proving no tampering.

### 🟢 Sprint 8: Beta Launch & Hardening
**Goal:** Make it ready for early users (Universities, local gas processors).
**Deliverables:**
1.  Security audit on the API (rate limiting, input sanitization).
2.  `docs/API_DOCUMENTATION.md` and `docs/USER_GUIDE.md`.
3.  Docker Compose file to deploy the frontend, backend, and database locally or on cloud providers.