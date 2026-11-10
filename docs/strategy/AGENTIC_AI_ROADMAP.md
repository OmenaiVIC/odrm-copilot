# Valoris: Agentic AI Architecture & Evolution Roadmap

**Status:** Living Document (CTO Approved)
**Date:** 2026-11-09

## 1. The Core Philosophy: The "Harness"
We are not building a chatbot. We are building an **Agent Harness**. 
A chatbot waits for a prompt and answers. A harness runs the AI in a loop, gives it tools to interact with the world, and manages its memory. 

---

## 2. Phase 1: Pilot Integration (Current)
**Goal:** A stable, secure, single-turn agent that can answer follow-up questions.
*   **Architecture:** Native stateless history passing (`messages[]` array).
*   **Implementation:** Sprint 8 (Current).
*   **Why this approach:** For a 90-day pilot with 3 operators, passing the raw conversation history back and forth from the frontend to Gemini is the most reliable, cheapest, and lowest-latency method. 

---

## 3. Phase 2: NUPRC National Integration (Post-Pilot)
**Goal:** The agent must remember users across different days, automate compliance workflows, and integrate with NOGIET.

*   **Resource 1: Mem0 (https://github.com/mem0ai/mem0) - Long-Term Memory**
    *   *Why:* When NUPRC has hundreds of users, we cannot send a 100-message history array on every request. Mem0 extracts facts and stores them in a vector database.
*   **Resource 2: n8n (https://github.com/n8n-io/n8n) - Workflow Automation**
    *   *Why:* To visually build workflows for automated monthly ESG reports.
*   **Resource 3: NOGIET Data Integration Tool**
    *   *Why:* We will build a new LangChain tool called `fetch_nogiet_hotspots`. This will allow the NUPRC auditor to ask the agent: *"Are there any hotspots at Site A, and is it profitable to capture them?"* The agent will call the NOGIET API, cross-reference it with the Valoris TEA engine, and generate the answer.

---

## 4. Phase 3: Operational Intelligence & Cryptographic ESG
**Goal:** A fully autonomous, multi-agent system that can research, simulate, and audit.

*   **Resource 1: LangChain Deep Agents (https://github.com/langchain-ai/deepagents)**
*   **Resource 2: CrewAI (https://github.com/crewAIInc/crewAI)**
*   **Resource 3: Browser-Use (https://github.com/browser-use/browser-use)**
*   **Resource 4: Dexter (https://github.com/virattt/dexter)**

## 5. Continuous Learning (CTO Note)
*   **Microsoft AI Agents for Beginners:** The CTO is currently studying this curriculum (https://github.com/microsoft/ai-agents-for-beginners) to ensure the theoretical foundation of our architecture aligns with industry standards. (Not a codebase sprint, just professional development).