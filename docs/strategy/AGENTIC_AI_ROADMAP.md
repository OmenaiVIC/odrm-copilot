# Valoris: Agentic AI Architecture & Evolution Roadmap

**Status:** Living Document (CTO Approved)
**Date:** 2026-11-09

This document outlines the architectural philosophy for the Valoris AI Agent and maps out the specific tools and frameworks we will adopt as we transition from Phase 1 (Pilot) to Phase 3 (Cryptographic ESG).

## 1. The Core Philosophy: The "Harness"
We are not building a chatbot. We are building an **Agent Harness**. 
A chatbot waits for a prompt and answers. A harness runs the AI in a loop, gives it tools to interact with the world (our ML models, our TEA engine), and manages its memory. The resources below are evaluated based on how they improve our harness.

---

## 2. Phase 1: Pilot Integration (Current)
**Goal:** A stable, secure, single-turn agent that can answer follow-up questions.

*   **Architecture:** Native stateless history passing (`messages[]` array).
*   **Implementation:** Sprint 8 (Upcoming).
*   **Why this approach:** For a 90-day pilot with 3 operators, passing the raw conversation history back and forth from the frontend to Gemini is the most reliable, cheapest, and lowest-latency method. It requires zero new infrastructure.

---

## 3. Phase 2: NUPRC National Integration (Post-Pilot)
**Goal:** The agent must remember users across different days, automate compliance workflows, and handle multi-step reasoning.

*   **Resource 1: Mem0 (https://github.com/mem0ai/mem0) - Long-Term Memory**
    *   *Why:* When NUPRC has hundreds of users, we cannot send a 100-message history array on every request (it will crash the context window and cost too much). Mem0 sits between our agent and Gemini. It extracts facts ("Operator A prefers 850°C") and stores them in a vector database. 
    *   *Action:* We will replace our stateless array with a Mem0 vector layer.
*   **Resource 2: n8n (https://github.com/n8n-io/n8n) - Workflow Automation**
    *   *Why:* In Phase 2, we promised NUPRC automated monthly ESG reports. Instead of writing custom Python cron jobs, we will use n8n to visually build workflows (e.g., "On the 1st of every month, query the Valoris API, generate the PDF, and email it to the Commission").
*   **Resource 3: Ralph (https://github.com/snarktank/ralph) - The Loop Pattern**
    *   *Why:* Our current agent stops after one tool call. In Phase 2, we might want it to: *Plan → Call API → Check Result → Adjust → Call API again → Generate Report*. Ralph is a reference implementation for this "keep going until the job is done" loop.

---

## 4. Phase 3: Operational Intelligence & Cryptographic ESG
**Goal:** A fully autonomous, multi-agent system that can research, simulate, and audit.

*   **Resource 1: LangChain Deep Agents (https://github.com/langchain-ai/deepagents) - The Harness Upgrade**
    *   *Why:* As the agent's responsibilities grow (monitoring 28 sites, planning maintenance, writing reports), our custom `AgentService` will become too complex. Deep Agents provides a higher-level harness with built-in planning, sub-agent spawning, and long-term memory.
*   **Resource 2: CrewAI (https://github.com/crewAIInc/crewAI) - Multi-Agent Collaboration**
    *   *Why:* For Phase 3, we want to simulate a team. Instead of one AI, we will have a "Crew" of agents: A *Regulatory Agent* checking compliance, a *Financial Agent* analyzing carbon credits, and a *Chemistry Agent* checking physics bounds. CrewAI allows them to collaborate.
*   **Resource 3: Browser-Use (https://github.com/browser-use/browser-use) - Autonomous Web Interaction**
    *   *Why:* If an operator uses a web-based SCADA system (or even email attachments) to log their data, Browser-Use can autonomously log in and extract the data, saving us weeks of manual data wrangling.
*   **Resource 4: Dexter (https://github.com/virattt/dexter) or GPT-Researcher (https://github.com/assafelovic/gpt-researcher)**
    *   *Why:* NUPRC will eventually want the agent to generate "Investment Memos." These agents can autonomously research carbon market trends, scrape news, and write a 5-page analyst report.

---

## 5. Continuous Learning (CTO Note)
*   **Microsoft AI Agents for Beginners:** The CTO is currently studying this curriculum (https://github.com/microsoft/ai-agents-for-beginners) to ensure the theoretical foundation of our architecture aligns with industry standards. (Not a codebase sprint, just professional development).