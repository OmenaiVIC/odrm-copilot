# Valoris Master Roadmap & Commercial Strategy

## PART 1: CTO Architectural Blueprint

**Product Name:** Valoris (Internal Engineering Codename: *ODRM-Copilot / Syngas Shovel*)
**Core Value Proposition:** A B2B SaaS platform that uses Surrogate AI and Agentic workflows to predict, optimize, and financially model Oxy-Dry Reforming of Methane (ODRM). 
Valoris is designed as a regulator-agnostic "Action Layer" that sits on top of any public methane-detection source — turning satellite-detected emissions into profitable business cases. NOGIET-style (Nigerian Oil and Gas Industry Emission Tracker) emission tracking is one example of an upstream detection source, not a required integration.

### 1. The Tech Stack
*   **Frontend:** Next.js (React), Tailwind CSS, TanStack Query, React-Markdown.
*   **Backend API:** FastAPI (Python).
*   **Data Layer:** PostgreSQL, Parquet.
*   **Machine Learning:** XGBoost.
*   **Agentic Layer:** LangChain, `langchain-google-genai`.
*   **The Evidence Chain:** A Merkle-tree based logging system for immutable ESG/Carbon reports and tokenization.

### 2. System Flow
1.  **Detection:** A public satellite system surfaces a methane hotspot at Site A. Valoris accepts any `DetectionSource` that returns schema-compliant hotspot data; NOGIET-style is one example adapter.
2.  **User Input:** The operator (or an accredited researcher, NGO, or regulator in the public-good tier) opens Valoris and inputs the site's conditions.
3.  **Agent Orchestrator:** Parses intent, validates physics bounds.
4.  **Surrogate Model:** Runs inference in <50ms (predicting CH4 Conversion, Syngas Yield).
5.  **TEA Engine:** Calculates the financial ROI based on current gas prices and carbon credit values.
6.  **Output:** A dashboard with the optimal operating parameters, risk warnings, and an ESG report proving the **Economic Solution** to the detected emission.

---

## PART 2: PMBOK Governance & Commercial Model

**Blue Ocean Strategy (Shovel-and-Picks):**
We sell the "picks" (software optimization) to the "miners" (plant operators). We do not own the physical reactors; we own the intelligence that makes them profitable. 

### The 3-Phase Commercial Strategy
Valoris is not a standalone SaaS. It is a regulatory-alignment strategy designed for national-scale use cases.

Public-Good Tier (whitelist): Valoris operates a self-service whitelist that grants free access to the dashboard and ESG export for **(a) NGFCP PAFG permit holders who prove their permit,** **(b) accredited university researchers,** **(c) NGOs,** and **(d) regulators.** 
No bilateral agreement required. The whitelist is the mechanism by which Valoris serves the public good without claiming a regulator partnership.

**Status note:** Valoris has no signed agreement with NUPRC, NOGIET, or any NGFCP (Nigerian Gas Flare Commercialisation Programme) operator at this writing. References to NUPRC, NOGIET, and the 28 NGFCP PAFG (Permits to Access Flare Gas) holders describe public programs and target use cases.

*   **Phase 1: The Pilot Integration Mandate (Current)**
    *   *Target use case:* NGFCP permit holders and a regulatory dashboard aligned with NOGIET's mission.
    *   *Offer:* Train our AI on their real-world historical data and provide a Regulatory Dashboard to track compliance.
    *   *Revenue:* A Pilot Mandate Grant (non-dilutive funding).
    *   *Purpose:* Prove technical feasibility on real-world "dirty gas" and establish Valoris as the regulatory standard.
    
*   **Phase 2: The National Integration (Post-Pilot)**
    *   *Target use case:* National rollout aligned with NOGIET and the 28 PAFG holders issued under NGFCP.
    *   *Offer:* Designed for integration with a NOGIET-style platform; onboarding of NGFCP operators at scale.
    *   *Revenue:* Annual government licensing fee + B2B SaaS subscriptions from the operators.
    *   *Purpose:* Ecosystem fit. We are positioned to become a candidate "Regulatory Command Center" for Nigeria if and when the regulator elects national rollout. 

*   **Phase 3: Operational Intelligence & Cryptographic ESG (Tokenization)**
    *   *Target:* International ESG Investors & Global South Operators.
    *   *Offer:* Predictive Maintenance and **Tamper-Proof Carbon Credits** (Merkle-tree verified and tokenized on-chain using Stellar's Soroban smart contracts for protocol-level compliance).
    *   *Revenue:* Premium SaaS tier + transaction fees on verified, tradeable carbon credits.
    *   *Purpose:* Global expansion, unlocking international liquidity for African carbon credits through regulated, compliant RWA tokenization.

### Risk Register (Probability-Impact)
| Risk ID | Risk Description | Prob | Impact | Score | Mitigation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-001** | Data Scarcity (No real simulator data) | 3 | 4 | 12 | Use the Kahobe thesis data to bootstrap, then retrain during the Phase 1 Pilot. |
| **R-002** | Agent Hallucination | 2 | 5 | 10 | Hard-coded physics guardrails. The LLM cannot pass data to the ML model unless it fits a strict schema. |
| **R-003** | User Trust (Engineers don't trust AI) | 4 | 3 | 12 | Show the "Evidence Chain" and utilize strict schemas to prove the math is auditable. |

---

## PART 3: Sprint Execution Roadmap

### 🟢 Sprints 1–7 (Complete)
Data Engineering, ML Surrogate, TEA Engine, UI/Market Data/Evidence Chain, Agentic Orchestrator, ESG Export, Beta Launch & Hardening. See `docs/SPRINT_*_REPORT.md` for each.

### 🟢 Sprint 8 (Complete): Multi-Turn Memory & Agent Context
The `/api/v1/chat` endpoint accepts a `messages[]` array. Backend trims context to prevent token overflow. Report: `docs/SPRINT_8_REPORT.md`.

### 🟡 Sprint 9 (In progress): Detection-Adapter Foundation & Predictive Maintenance
**Goal:** Build the regulator-agnostic detection adapter and predictive-maintenance UI. Real-data ingestion remains blocked, but the interface and mock adapter ship.

**Deliverables:**
1. `DetectionSource` interface (pluggable, async). Unit tests for interface; mock adapter returns fixture data.
2. Mock NOGIET-style adapter that returns schema-compliant hotspot lists. Documented as example, not integration.
3. Predictive Maintenance UI panel: Carbon-risk >80% triggers warning banner. Tested in Vitest.
4. **Security hardening** carried over from legacy SECURITY.md: RBAC, Refresh Tokens, CSP, MFA for admins, Redis-backed JWT revocation.
5. Real-data adapter: explicitly out of scope, documented as future work requiring a formal data agreement.

**Gate:** Sprint 9 complete when interface, mock adapter, UI panel, and security hardening have passing tests. Real-data adapter does not block completion.

### 🟡 Sprint 10 (Planned): Open Public-Good Dashboard + Verifiable ESG Export
**Goal:** Ship the Mozilla Q1 "Public Release" milestone deliverables.

**Deliverables:**
1. Whitelist access flow: application, vetting against public-good criteria, dashboard provisioning. Backend endpoints and frontend form. Tested.
2. Merkle-tree ESG audit trail: each screening produces a hash chain; verifier endpoint. Tested.
3. Open benchmark publication: dataset, validator, baseline XGBoost model packaged for public release. MIT license. Documented reproduction steps.
4. Detection adapter wired into dashboard: dashboard shows hotspots from any `DetectionSource`; mock shown by default.

**Gate:** Sprint 10 complete when all four deliverables are tested and the open benchmark is published to GitHub with a versioned release tag.

### 🟡 Sprint 11 (Planned): Open Educational Layer + RWA Prototype
**Goal:** Mozilla Q2–Q4 deliverables plus research-stage tokenization prototype.

**Deliverables:**
1. Tutorials and video-guide scripts in `docs/tutorials/`, validated by a new user following them.
2. Workshop materials: slide deck and facilitator guide for Nigerian universities and regulator training.
3. Feedback capture pipeline: endpoint and UI that feed the v1.0 backlog.
4. RWA tokenization prototype on Stellar/Soroban: proof-of-concept contract, documented as research output, not product.

**Gate:** Sprint 11 complete when tutorials are validated, workshops materials are drafted, feedback pipeline is tested, and the tokenization prototype is documented.

---

## PART 4: Dual Funding Strategy & Public Good
Valoris operates a dual-layer architecture that appeals to both non-profit public-good funders and commercial venture accelerators.

*   **Public Goods Grants:** We pursue non-dilutive grants to fund the open-source benchmark, the 10,000-scenario dataset, educational materials, and community workshops. These are permanent public goods for the Global South, ensuring that local researchers and regulators always have free access to the fundamental physics tools.
*   **Commercial Accelerators:** We pursue commercial funding (SAFE notes, equity) to fund the proprietary SaaS engine, the tokenization roadmap (Stellar/Soroban), and our prospective national regulator's pilot. These are the revenue engines that ensure the company can sustain itself, pay salaries, and scale globally.
*   *The Synergy:* The open-source foundation acts as a massive "freemium" acquisition funnel. Researchers who learn on the free MIT tool graduate to the proprietary SaaS when they enter the workforce. The commercial engine then funds the continued maintenance of the public good.