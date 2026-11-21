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

## Known Cleanup
- The previous content of this file duplicated `MASTER_ROADMAP.md` with conflicting sprint numbers (Sprint 8 = Pilot Integration here vs. Multi-Turn Memory in MASTER_ROADMAP). That content has been removed and the sprint schedule consolidated into `MASTER_ROADMAP.md`.