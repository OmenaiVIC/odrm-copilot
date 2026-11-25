# Valoris Security Hardening Roadmap

**Status:** Superseded by `docs/strategy/MASTER_ROADMAP.md` for sprint scheduling. This file retains security-specific deliverables only.

## Completed (Sprints 1–7)
- JWT authentication
- API rate limiting
- Docker Compose isolation
- `.env.docker` excluded from git

## Sprint 9 Security Deliverables (carried into revised Sprint 9)
1. **Role-Based Access Control (RBAC):** Distinct roles for admin, public-good-tier user, and commercial-tier user.
2. **Refresh Tokens:** Short-lived access tokens with rotating refresh tokens.
3. **Content Security Policy (CSP):** Strict CSP headers on the Next.js frontend.
4. **Multi-Factor Authentication (MFA):** Required for admin accounts.
5. **Redis-backed JWT revocation:** Immediate token invalidation on logout or role change.

## Public-Good Tier Security Note
Whitelist vetting (NGFCP permit verification, university affiliation verification, NGO status verification) must be logged with the same audit rigor as commercial-tier onboarding. Whitelist status is a security-relevant attribute and must be checked server-side on every dashboard request, not trusted from the client.

## Audit Readiness Cross-Reference

Working cross-reference between existing/planned security work and the Audit Readiness Checklist. Exhaustive audit is Sprint 12.

| Item | Existing Evidence | Gap |
|---|---|---|
| Scope traceability | Sprint plans carry scope sections | Retroactive scope review for Sprints 1–11 |
| Repo hygiene | README, MIT LICENSE, documented structure | CONTRIBUTING.md, CODE_OF_CONDUCT.md missing |
| Integration tests | 604 backend tests, frontend Vitest | `docs/INTEGRATION_TESTS.md` inventory missing |
| Threat model | Partial: physics guardrails, evidence chain, JWT auth documented across sprints | Full `docs/THREAT_MODEL.md` missing (Sprint 12) |
| Dataflow diagram | Partial: system-flow section of MASTER_ROADMAP.md | Formal `docs/DATAFLOW.md` with trust boundaries missing (Sprint 12) |
| Cryptographic correctness | `LEAF_PREFIX` / `NODE_PREFIX` domain separation; tamper fixtures in D2a integration tests | Consolidated evidence doc (Sprint 12) |
| LLM boundary integrity | Guardrails in `agents/guardrails.py`; tests in `backend/tests/unit/` | Explicit threat assessment in `THREAT_MODEL.md` (Sprint 12) |
| Personal data handling | Whitelist verification logic shipped (D1) | Retention/access policy in `THREAT_MODEL.md` (Sprint 12) |
| Tooling scan (bonus) | None | `pip-audit`/`npm audit`/`cargo-audit` runs in Sprint 12 |
| Remediation plan (bonus) | None | Produced from Sprint 12 scan findings |
| Dependency review (bonus) | Ad hoc; `openpyxl` added in D2a without CVE check | Formalise in Phase 4 workflow (effective D3) |

### Forward-Sprint Impact

- **Sprint 11 (current):** D3, D4, D5 each evaluated against the checklist in Phase 2 (effective D3).
- **Sprint 12 (planned):** Retroactive audit of Sprints 1–11 and production of missing artifacts.
- **External release / tag:** Blocked until Sprint 12 closes.

### New Phase 2 requirement (effective D3)

Every sprint plan must include an "Audit Readiness Impact" section. See `docs/SPRINT_WORKFLOW.md`.

## Known Cleanup
- The previous content of this file duplicated `MASTER_ROADMAP.md` with conflicting sprint numbers (Sprint 8 = Pilot Integration here vs. Multi-Turn Memory in MASTER_ROADMAP). That content has been removed and the sprint schedule consolidated into `MASTER_ROADMAP.md`.