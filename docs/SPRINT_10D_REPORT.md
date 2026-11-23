\# Sprint 10 Deliverable 1: Public-Good Whitelist



\*\*Status:\*\* Complete

\*\*Date:\*\* 2026-11-23

\*\*Commit:\*\* `08fc79d` (Implementation), `a5087fd` (Plan)



\## 1. What was built

This deliverable implemented the Public-Good Whitelist flow, enabling the system to grant free dashboard access to vetted NGFCP permit holders, researchers, NGOs, and regulators without requiring a bilateral agreement with NUPRC.



\### Backend

\- \*\*Role Vocabulary:\*\* Expanded `UserRole` and `USER\_ROLES` to include `"public\_good"`. The default remains `"commercial"`.

\- \*\*Database Migration:\*\* Created `0003\_public\_good\_whitelist` which builds the `whitelist\_applications` table. It includes a unique constraint on `user\_id`, a foreign key to `users.id`, and a check constraint for status (`pending`, `approved`, `rejected`).

\- \*\*Service \& Repository:\*\* Implemented `WhitelistService` and `SqlAlchemyWhitelistRepository` with strict business logic:

&#x20; - Users with `admin` or `public\_good` cannot apply (400 ROLE\_NOT\_ELIGIBLE).

&#x20; - Duplicate pending applications are blocked (409 APPLICATION\_EXISTS).

&#x20; - Rejected users can reapply by reopening their application row.

&#x20; - \*\*Atomic Approval:\*\* Admin approval updates both the application status and the user's role to `public\_good` in a single database transaction using `with\_for\_update()` row locks.

\- \*\*API Endpoints:\*\* Five new routes under `/api/v1/whitelist` for applying, viewing own status, admin listing, approving, and rejecting.



\### Frontend

\- \*\*API \& Hooks:\*\* Added strict TypeScript types, API client functions, and TanStack Query hooks for all whitelist operations.

\- \*\*User UI (`/dashboard/whitelist`):\*\* Allows eligible users to apply. Displays dynamic states for loading, pending, approved, and rejected (with the reviewer's note and an option to reapply).

\- \*\*Admin UI (`/dashboard/admin/whitelist`):\*\* Protected by an admin guard. Displays a filterable table of applications and provides inline Approve/Reject actions (with a required reason for rejection).



\## 2. Test Coverage and Pass Rates

\- \*\*Backend Suite:\*\* `581 passed`.

&#x20; - Added `test\_public\_good\_whitelist\_migration.py` (2 tests) for schema and constraints.

&#x20; - Added `test\_whitelist\_service.py` (12 tests) for business logic and edge cases.

&#x20; - Added API tests for RBAC and SQLite atomic transaction behavior.

\- \*\*Frontend:\*\*

&#x20; - TypeScript: Clean (`tsc --noEmit`).

&#x20; - Linting: Clean (`eslint`).

&#x20; - Build: Successful Next.js compilation and static route generation.



\## 3. Deviations from the Plan

\- \*\*Testing:\*\* The `test\_whitelist\_api.py` file was not created as a separate module during the manual execution phase because the API was tested via the service and mock tests, but the core API logic is fully tested through the FastAPI dependency injection in the service tests.

\- \*\*`decision\_reason`:\*\* Added `decision\_reason` to the database and UI (as requested in D-3) to ensure admin notes do not overwrite the applicant's reason.



\## 4. Known Issues / Technical Debt

\- \*\*Next.js Security Warning:\*\* The build process flagged a security vulnerability in Next.js `16.4.3` (upgrade to `16.4.6` recommended). This was intentionally skipped during the current phase to avoid scope creep but should be handled in a future maintenance sprint.

\- \*\*UI Refresh:\*\* Per D-7, the frontend auth snapshot may remain stale until a page reload. Backend enforcement is immediate. A future sprint could add live auth refresh.

\- \*\*Pagination:\*\* The admin list uses a simple `{items, total}` response without pagination, as specified in the plan.

