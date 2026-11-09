# Valoris Master Roadmap & Commercial Strategy

## PART 1: CTO Architectural Blueprint

**Product Name:** Valoris (Internal Engineering Codename: *ODRM-Copilot / Syngas Shovel*)
**Core Value Proposition:** A B2B SaaS platform that uses Surrogate AI and Agentic workflows to predict, optimize, and financially model Oxy-Dry Reforming of Methane (ODRM). It bypasses the need for $50k/year simulation software licenses and years of specialized training, democratizing process engineering for the Global South.

### 1. The Tech Stack
*   **Frontend:** Next.js (React), Tailwind CSS, TanStack Query, Recharts (for interactive thermodynamics curves), Vercel (Hosting).
*   **Backend API:** FastAPI (Python).
*   **Data Layer:** PostgreSQL (User profiles, project data), Parquet (Storing ODRM datasets).
*   **Machine Learning (The Surrogate):** XGBoost.
*   **Agentic Layer:** LangChain, `langchain-google-genai`. An LLM translates natural language into structured tool calls (ML inference, TEA calculator).
*   **The Evidence Chain:** A Merkle-tree based logging system that hashes every prediction, input parameter, and model version used, generating immutable ESG/Carbon reports.

### 2. System Flow
1.  **User Input:** Natural language or form input (Feed composition, Temp, Pressure).
2.  **Agent Orchestrator:** Parses intent, validates physics bounds (e.g., Temp < 1000°C).
3.  **Surrogate Model:** Runs inference in <50ms (predicting CH4 Conversion, Syngas Yield).
4.  **TEA Engine:** Calculates the financial ROI based on current gas prices and carbon credit values (via the Market Data Service).
5.  **Output:** A dashboard with the optimal operating parameters, risk warnings, and an ESG report.

---

## PART 2: PMBOK Governance & Commercial Model

**Blue Ocean Strategy (Shovel-and-Picks):**
We sell the "picks" (software optimization) to the "miners" (plant operators, university researchers, local gas processors). We do not own the physical reactors; we own the intelligence that makes their reactors profitable and safe. 

### Risk Register (Probability-Impact)
| Risk ID | Risk Description | Prob | Impact | Score | Mitigation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-001** | Data Scarcity (No real simulator data) | 3 | 4 | 12 | Use the Kahobe thesis data to bootstrap, then retrain during the Phase 1 Pilot. |
| **R-002** | Agent Hallucination | 2 | 5 | 10 | Hard-coded physics guardrails. The LLM cannot pass data to the ML model unless it fits a strict schema. |
| **R-003** | User Trust (Engineers don't trust AI) | 4 | 3 | 12 | Show the "Evidence Chain" and utilize strict schemas to prove the math is auditable. |

---

## PART 3: Sprint Execution Roadmap (Sprint 1 to Sprint 10)

*All sprints strictly follow the 5-Phase workflow defined in `docs/SPRINT_WORKFLOW.md`: Constitution → Plan-First → Review Gate → Implementation → Report.*

### 🟢 Sprint 1: Data Engineering (The Foundation)
**Goal:** Generate the dataset that the AI will learn from.
**Deliverables:** Generator script, 10,000-row dataset, strict schema validator.

### 🟢 Sprint 2: Surrogate ML Model (The Brain)
**Goal:** Train an ML model that replaces slow physics simulation.
**Deliverables:** XGBoost model (R² > 0.95), FastAPI route `/api/predict`.

### 🟢 Sprint 3: TEA Engine (The Money)
**Goal:** Turn the AI predictions into actionable financial ROI.
**Deliverables:** Pure financial engine (`backend/src/odrm/domain/tea.py`), FastAPI route `POST /api/v1/tea`.

### 🟢 Sprint 4: Core UI/UX, Market Data & Evidence Chain
**Goal:** A beautiful frontend fed by live market prices.
**Deliverables:** Next.js dashboard, Market Data Service (`GET /api/v1/market-prices`), Evidence Chain UI.

### 🟢 Sprint 5: Agentic Orchestrator (The Interface)
**Goal:** Allow users to ask questions in plain English.
**Deliverables:** LangChain agent, `calculate_project_economics()` tool, strict guardrails.

### 🟢 Sprint 6: The ESG Export Engine (Automated Compliance)
**Goal:** Fulfill the pitch deck promise of automated compliance reporting.
**Deliverables:** `POST /api/v1/report` (PDF generation), "Download ESG Report" button.

### 🟢 Sprint 7: Beta Launch & Hardening (The Production Layer)
**Goal:** Secure the platform and prepare it for real users.
**Deliverables:** JWT Auth (Argon2id), API Rate Limiting, Docker Compose stack, UI Rebrand to Valoris.

### 🟢 Sprint 8: Multi-Turn Memory & Agent Context (The Conversation)
**Goal:** Transform the AI into a conversational partner that remembers context.
**Deliverables:** Update `ChatRequest` to accept `messages[]`, update React state to send history, implement context window management.

### 🟡 Sprint 9: Real-World Pilot Integration (Blocked pending NUPRC Data)
**Goal:** Make the product usable for real-world, dirty gas.
**Deliverables:** Train on real-world data from 3 NGFCP operators, "Predictive Maintenance" UI output, RBAC security hardening.

### 🟡 Sprint 10: Cryptographic ESG & Carbon Accounting (Blocked pending Pilot)
**Goal:** Provide the immutable audit trail for carbon credits.
**Deliverables:** Merkle-tree cryptographic hash chain, secure ESG report export, Redis-backed JWT revocation.