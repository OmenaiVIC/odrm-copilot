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

## Audit Readiness Requirements (Mandatory Gate)

Every deliverable is evaluated against the Audit Readiness Checklist below. Non-compliance on any mandatory item blocks release, tag, or external submission until remediated or explicitly deferred with CTO sign-off.

### Mandatory Items

| # | Item | Required Evidence | Home |
|---|---|---|---|
| 1 | Scope traceability | Written scope statement, funding/source context, and deliverable boundary | Sprint plan §1 |
| 2 | Repo hygiene | Clear structure, README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, no dead code, naming consistency | Repo root |
| 3 | Integration tests | Test files exist AND executed (raw output pasted in Phase 4) | `backend/tests/integration/`, frontend Vitest |
| 4 | Threat model | Written model referencing dataflow, enumerated threats, severity, mitigations, residual risk | `docs/THREAT_MODEL.md` |
| 5 | Dataflow diagram | Diagram with trust boundaries, data entities, and directional flows | `docs/DATAFLOW.md` |
| 6 | Cryptographic correctness | Evidence chain domain separation, Merkle proof construction, and verifier logic tested against tamper fixtures | `backend/tests/integration/test_evidence_*.py` |
| 7 | LLM boundary integrity | Prompt injection / jailbreak surface assessed; guardrails tested; LLM cannot bypass physics or financial validation | `backend/tests/unit/test_guardrails*.py`, `docs/THREAT_MODEL.md` |
| 8 | Personal data handling | Whitelist verification data classified; retention and access policy documented | `docs/THREAT_MODEL.md`, `docs/SECURITY.md` |

### Bonus Items

| # | Item | Required Evidence | Home |
|---|---|---|---|
| 9 | Tooling scan | Automated scan output dated within 30 days of release/tag (`pip-audit`, `npm audit`, `cargo-audit`, `bandit`) | `docs/SECURITY_SCANS/` |
| 10 | Remediation plan | Findings triaged with severity, fix status, and owner | `docs/THREAT_MODEL.md` §Remediation |
| 11 | Dependency review | New dependencies reviewed against CVE feeds before commit | Phase 4 evidence |

### Phase 2 addition (Plan-First)

Every `docs/SPRINT_X[Y]_PLAN.md` must include an **Audit Readiness Impact** section:
- Which of the 11 items this deliverable affects
- Which evidence it produces
- Which evidence it defers (and to which sprint)
- Sprints with no impact must state so explicitly

### Phase 3 addition (Review Gate)

For sprints touching security-sensitive surfaces (auth, evidence chain, LLM prompt path, cryptographic primitives, external contract integration):
- Phase 3 review includes a diff of `docs/THREAT_MODEL.md` and `docs/DATAFLOW.md`, OR an explicit deferral note if those files do not yet exist.

### Phase 4 addition (Implementation)

- Any new integration test must be executed and its raw output pasted in Phase 4 evidence.
- Any new dependency (`pyproject.toml`, `package.json`, `Cargo.toml`) must be checked against known-vulnerability feeds (`pip-audit`, `npm audit`, `cargo-audit`) before commit. Output pasted.

### Phase 5 addition (Report)

The sprint report must include an **Audit Readiness Status** section:
- Mandatory items: status (compliant / partial / N/A / deferred)
- Bonus items: status
- Deferred items with rationale and target sprint
