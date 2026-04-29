# Testing Strategy

## Priorities
- core-service model constraints and CRUD smoke tests
- core-service token auth flow (`signup/login/refresh/logout/me/introspect`)
- core-service planning snapshot export and internal planner access
- eligibility logic
- scoring logic
- planning constraints
- planner artifact persistence and retrieval
- assignment approval flow
- shared contracts validation for planning windows and proposal dates

## Basic checks
- core-service: local startup, migration workflow, authenticated CRUD smoke tests, model constraints, serializer validation, planning snapshot export for authenticated users and internal token calls
- core-service auth: public signup/login, refresh via HttpOnly cookie, logout cookie clear, `me` payload shape, inactive user login/refresh denial, introspection allowed only with internal token
- core-service user profile sync: manager/employee user create and role-change auto-create `Employee` profile; employee->admin role change keeps existing profile
- core-service RBAC: role matrix checks for admin/manager/employee, employee self-scope checks for schedule/leaves, manager-only approval path, and admin-only users API
- core-service approval flow: persisted planner proposal lookup, idempotent replay for the same `task + employee + source_plan_run_id`, rejection of missing or non-selected proposals, rejection of second final assignment for one task, upstream planner failure handling, and internal-token reread of planner-service after planner auth gate
- planner-service: unit and integration tests for planning pipeline, `CreatePlanRunRequest` boundary, snapshot client failure handling, SQLite persistence of run/snapshot/proposals/unassigned/solver stats, persisted run retrieval for manager review, overlap conflict diagnostics, and weighted score stability
- planner-service auth gate: Bearer header validation, deny employee role, allow manager/admin role, and controlled `503` when core introspection is unavailable
- frontend-app: install dependencies, type-check the Vue shell, build production bundle, verify containerized Vite startup via `docker compose`, and manually verify token auth, guarded routing, RBAC gating, and employee self-service CRUD
- contracts: schema compatibility between services

## Suggested MVP Commands

```bash
# Core service
cd services/core-service
poetry install
poetry run python manage.py makemigrations --check
poetry run python manage.py check
poetry run python manage.py safe_migrate
poetry run python manage.py test

# Core service quick unit checks without a local PostgreSQL container
DJANGO_TEST_SQLITE=true poetry run python manage.py test

# Planner service
cd services/planner-service
poetry install
poetry run pytest -q

# Frontend app
cd frontend-app
npm install
npm run type-check
npm run build

# Container smoke
cd /path/to/repo
docker compose up --build

# Frontend container only
docker compose up --build frontend-app
```

If `core-service` detects `InconsistentMigrationHistory` in local PostgreSQL, `safe_migrate` can auto-recover
by resetting `public` schema when `CORE_DB_AUTO_RESET_ON_INCONSISTENT_MIGRATIONS=true` (default).
If you prefer manual full reset before repeating the smoke:

```bash
docker compose down -v
docker compose up --build
```

## Frontend Manual Smoke

- Preferred runtime: `docker compose up --build` from the repository root.
- Optional alternative: start backend in Docker and run `frontend-app` on the host with `npm run dev`.
- Start backend services and the frontend shell locally.
- Open `http://localhost:5173`.
- As anonymous user, verify protected routes redirect to `/login` and `/signup` stays guest-only.
- Verify login works for existing manager/admin accounts and the app bootstrap restores session after reload through refresh cookie.
- Verify signup creates an employee account and lands inside the protected shell with employee role.
- Verify logout clears session and returns the browser to `/login`.
- As manager/admin, verify sidebar navigation exposes `Reference Data`, `Tasks`, `Planning`, and `Assignments`.
- As employee, verify sidebar hides `Reference Data`, `Planning`, and `Assignments`, and instead shows `My Schedule` and `My Leaves`.
- On `Reference Data`, verify manager does not see `users` CRUD and only gets the allowed action set for departments, skills, and employees.
- On `Tasks`, verify task create uses the authenticated user from `/auth/me` and no longer requires reading `/users/`.
- On `Planning`, verify manager/admin can launch a plan run with period-only scope, optional department filter, and optional selected task subset.
- Verify the planning launch summary shows the returned `plan_run_id`, status, assigned count, and unassigned count after `POST /api/v1/plan-runs`.
- Verify entering a persisted `plan_run_id` reloads the run through `GET /api/v1/plan-runs/{plan_run_id}`.
- Verify the persisted review screen renders proposals, diagnostics, and solver statistics from planner-service.
- Verify only the selected proposal exposes the approval CTA.
- Verify approval sends only `task`, `employee`, `source_plan_run_id`, and optional notes to `POST /api/v1/assignments/approve-proposal/`.
- Verify the approval success state shows the returned final `Assignment` summary from `core-service`.
- Verify the browser does not ask the manager to re-enter assignment dates or planned hours during approval.
- On `Assignments`, verify the read-only list loads persisted records from `GET /api/v1/assignments/`.
- Verify assignment filters stay local-only and do not mutate backend state.
- If browser automation is unavailable in the environment, fall back to a live proxy smoke that still exercises `frontend -> /api|/planner-api -> core/planner` on real services.
- As employee, verify `Tasks` and `Task Requirements` are read-only.
- On `My Schedule`, verify employee CRUD for own `work-schedules` and `work-schedule-days`.
- On `My Leaves`, verify employee CRUD for own `employee-leaves`.
- Verify task and leave validation errors from backend are surfaced unchanged.
