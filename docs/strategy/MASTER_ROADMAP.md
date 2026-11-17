# Valoris Master Roadmap & Commercial Strategy

## PART 1: CTO Architectural Blueprint

**Product Name:** Valoris (Internal Engineering Codename: *ODRM-Copilot / Syngas Shovel*)
**Core Value Proposition:** A B2B SaaS platform that uses Surrogate AI and Agentic workflows to predict, optimize, and financially model Oxy-Dry Reforming of Methane (ODRM). Valoris acts as the **"Action Layer"** for the Nigerian Oil and Gas Industry Emission Tracker (NOGIET), turning satellite-detected emissions into profitable business cases for operators.

### 1. The Tech Stack
*   **Frontend:** Next.js (React), Tailwind CSS, TanStack Query, React-Markdown.
*   **Backend API:** FastAPI (Python).
*   **Data Layer:** PostgreSQL, Parquet.
*   **Machine Learning:** XGBoost.
*   **Agentic Layer:** LangChain, `langchain-google-genai`.
*   **The Evidence Chain:** A Merkle-tree based logging system for immutable ESG/Carbon reports and tokenization.

### 2. System Flow
1.  **NOGIET Detection:** The Commission's NOGIET satellite system detects a methane hotspot at Site A.
2.  **User Input:** The operator (or NUPRC auditor) opens Valoris and inputs the site's conditions.
3.  **Agent Orchestrator:** Parses intent, validates physics bounds.
4.  **Surrogate Model:** Runs inference in <50ms (predicting CH4 Conversion, Syngas Yield).
5.  **TEA Engine:** Calculates the financial ROI based on current gas prices and carbon credit values.
6.  **Output:** A dashboard with the optimal operating parameters, risk warnings, and an ESG report proving the **Economic Solution** to the NOGIET-detected problem.

---

## PART 2: PMBOK Governance & Commercial Model

**Blue Ocean Strategy (Shovel-and-Picks):**
We sell the "picks" (software optimization) to the "miners" (plant operators). We do not own the physical reactors; we own the intelligence that makes them profitable. 

### The 3-Phase Commercial Strategy
Valoris is not a standalone SaaS. It is a strategic national partnership model.

*   **Phase 1: The Pilot Integration Mandate (Current)**
    *   *Target:* NUPRC and 3 selected NGFCP operators.
    *   *Offer:* Train our AI on their real-world historical data and provide a Regulatory Dashboard to track compliance.
    *   *Revenue:* A Pilot Mandate Grant (non-dilutive funding).
    *   *Purpose:* Prove technical feasibility on real-world "dirty gas" and establish Valoris as the regulatory standard.
*   **Phase 2: The National Integration (Post-Pilot)**
    *   *Target:* NUPRC (National Rollout).
    *   *Offer:* Full integration into the NOGIET platform. Onboarding of all 28 NGFCP operators.
    *   *Revenue:* Annual government licensing fee + B2B SaaS subscriptions from the operators.
    *   *Purpose:* Deep lock-in. We become the "Regulatory Command Center" for Nigeria.
*   **Phase 3: Operational Intelligence & Cryptographic ESG (Tokenization)**
    *   *Target:* International ESG Investors & Global South Operators.
    *   *Offer:* Predictive Maintenance and **Tamper-Proof Carbon Credits** (Merkle-tree verified and tokenized on-chain).
    *   *Revenue:* Premium SaaS tier + transaction fees on verified, tradeable carbon credits.
    *   *Purpose:* Global expansion, unlocking international liquidity for African carbon credits.

### Risk Register (Probability-Impact)
| Risk ID | Risk Description | Prob | Impact | Score | Mitigation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-001** | Data Scarcity (No real simulator data) | 3 | 4 | 12 | Use the Kahobe thesis data to bootstrap, then retrain during the Phase 1 Pilot. |
| **R-002** | Agent Hallucination | 2 | 5 | 10 | Hard-coded physics guardrails. The LLM cannot pass data to the ML model unless it fits a strict schema. |
| **R-003** | User Trust (Engineers don't trust AI) | 4 | 3 | 12 | Show the "Evidence Chain" and utilize strict schemas to prove the math is auditable. |

---

## PART 3: Sprint Execution Roadmap

### 🟢 Sprint 1: Data Engineering (The Foundation)
*(Generate 10,000 synthetic physics rows, strictly validated.)*

### 🟢 Sprint 2: Surrogate ML Model (The Brain)
*(Train XGBoost models with R² > 0.95 and expose `/api/v1/predict`.)*

### 🟢 Sprint 3: TEA Engine (The Money)
*(Build the pure financial engine to calculate ROI, OPEX, and carbon credits.)*

### 🟢 Sprint 4: Core UI/UX, Market Data & Evidence Chain
*(Next.js dashboard, Market Data Service, and UI for model provenance.)*

### 🟢 Sprint 5: Agentic Orchestrator (The Interface)
*(LangChain agent to parse natural language and call the TEA tool with strict guardrails.)*

### 🟢 Sprint 6: The ESG Export Engine (Automated Compliance)
*(Generate professional PDFs with a SHA-256 cryptographic hash.)*

### 🟢 Sprint 7: Beta Launch & Hardening (The Production Layer)
*(JWT Auth, Rate Limiting, Docker Compose stack, UI Rebrand to Valoris.)*

### 🟢 Sprint 8: Multi-Turn Memory & Agent Context (The Conversation)
*(Update `ChatRequest` to accept `messages[]`, update React state, implement context window management.)*

### 🟡 Sprint 9: Real-World Pilot Integration (Blocked pending NUPRC Data)
*(Train on real-world data from 3 NGFCP operators, "Predictive Maintenance" UI output, RBAC security hardening.)*

### 🟡 Sprint 10: Cryptographic ESG & Carbon Accounting (Blocked pending Pilot)
*(Implement a Merkle-tree cryptographic hash chain and smart contracts for the tokenization of verified carbon credits.)*