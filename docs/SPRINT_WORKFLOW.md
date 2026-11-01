# Engineering Sprint Workflow

This document defines the strict operational rules for the OpenCode agent. Every sprint must follow this 5-phase lifecycle:

## Phase 1: Constitution & Skill Loading
- The agent must load the relevant `SKILL.md` files.
- The agent must read the `README.md` and the current Sprint Plan.
- **Rule:** No implementation code is written in this phase.

## Phase 2: Plan-First
- Before writing any code, the agent must write a `docs/SPRINT_X_PLAN.md` file.
- The plan must detail the technical approach, file structure, and testing strategy.
- **Rule:** The agent must STOP and wait for human authorization.

## Phase 3: Review Gate
- The human (CTO) reviews the plan. 
- If changes are needed, the agent revises the plan.
- Once approved, the human explicitly authorizes Phase 4.

## Phase 4: Implementation
- The agent executes the plan step-by-step.
- **Rule:** Test-Driven Development. Write the test first, then the code.
- The agent must run tests after every logical change. If a test fails, the agent must fix it before moving on.
- The agent must commit to Git after every successfully tested feature (e.g., `git commit -m "feat: added FastAPI prediction endpoint"`).

## Phase 5: Report
- The agent writes a `docs/SPRINT_X_REPORT.md` summarizing:
  1. What was built.
  2. Test coverage and pass rates.
  3. Any deviations from the original plan.
  4. Any known issues or technical debt.
