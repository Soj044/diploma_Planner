# Testing Strategy

## Priorities
- core-service model constraints and CRUD smoke tests
- core-service token auth flow (`signup/login/refresh/logout/me/introspect`) and `employee_profile` payload contract
- core-service frontend-facing read models for auth bootstrap and departments
- core-service planning snapshot export and internal planner access
- leave request/review workflow
- eligibility logic
- scoring logic
- planning constraints
- planner artifact persistence and retrieval
- final assignment flows (planner approval, manual assignment, rejection)
- shared contracts validation for planning windows and proposal dates

## Basic checks
- core-service: local startup, migration workflow, authenticated CRUD smoke tests, model constraints, serializer validation, nested department employee summaries without email, and planning snapshot export for internal token calls only
- core-service auth: public signup/login, refresh via HttpOnly cookie, logout cookie clear, `me` payload shape, `employee_profile` shape in `login/signup/refresh/me`, inactive user login/refresh denial, introspection allowed only with internal token
- core-service user profile sync: manager/employee user create and role-change auto-create `Employee` profile; employee->admin role change keeps existing profile
- core-service RBAC: role matrix checks for admin/manager/employee, employee read-only access to own schedules and schedule days, employee self-scope assignments visibility, requested-only employee leave mutation, manager/admin requested-leave queue, manager/admin-only approval/manual assignment paths, and admin-only users API
- core-service leave workflow: employee create forces `status=requested`, employee can update/delete only own `requested` leaves, employee cannot change leave status directly, and manager/admin can review requested leaves through `POST /api/v1/employee-leaves/{id}/set-status/` with `approved|rejected`
- core-service approval flow: persisted planner proposal lookup, manual final assignment creation, assignment rejection, idempotent replay for the same `task + employee + source_plan_run_id`, rejection of missing or non-selected proposals, rejection of second non-rejected final assignment for one task, manual assignment defaults (`start_date=task.start_date`, `end_date=task.due_date`, `source_plan_run_id=null`), upstream planner failure handling, and internal-token reread of planner-service after planner auth gate
- planner-service: unit and integration tests for planning pipeline, `CreatePlanRunRequest` boundary, snapshot client failure handling, SQLite persistence of run/snapshot/proposals/unassigned/solver stats, persisted run retrieval for manager review, overlap conflict diagnostics, and weighted score stability
- planner-service auth gate: Bearer header validation, deny employee role, allow manager/admin role, and controlled `503` when core introspection is unavailable
- frontend-app: install dependencies, type-check the Vue shell, build production bundle, verify containerized Vite startup via `docker compose`, and manually verify token auth, guarded routing, RBAC gating, and the current pre-Stage-1 employee UX limitations
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

## Stage 1 Backend Contract Smoke

- Verify `login`, `signup`, `refresh`, and `GET /api/v1/auth/me` all include `employee_profile` with `id`, `full_name`, `department_id`, `position_name`, `hire_date`, and `is_active`.
- Verify `GET /api/v1/departments/` returns nested employee summaries with `id`, `full_name`, and `position_name`, and does not expose nested employee email in that summary payload.
- Verify an `employee` token can only `list/retrieve` own `work-schedules` and `work-schedule-days`.
- Verify employee leave create always persists `status=requested`.
- Verify an `employee` token can update/delete only own `requested` leaves and cannot change leave status directly.
- Verify `manager` and `admin` can review requested leaves and call `POST /api/v1/employee-leaves/{id}/set-status/` with `approved|rejected`.
- Verify `GET /api/v1/assignments/` returns only own records for an `employee` token.
- Verify `POST /api/v1/assignments/manual/` creates a final `approved` assignment with `start_date=task.start_date`, `end_date=task.due_date`, and `source_plan_run_id=null`.
- Verify `POST /api/v1/assignments/{id}/reject/` marks the final assignment as rejected and reopens the task for a future non-rejected final assignment.
- Verify planner approval and manual assignment both reject creation of a second non-rejected final assignment for the same task.
- Verify single-task planning still uses the existing planner boundary `POST /api/v1/plan-runs` with `task_ids=[task.id]`.

## Frontend Manual Smoke

Stage 1 backend contracts intentionally move ahead of the current frontend employee screens.
Until the follow-up frontend slice lands, treat employee schedule/leave CRUD mismatches as expected integration debt rather than backend regressions.

- Preferred runtime: `docker compose up --build` from the repository root.
- Optional alternative: start backend in Docker and run `frontend-app` on the host with `npm run dev`.
- Start backend services and the frontend shell locally.
- Open `http://localhost:5173`.
- As anonymous user, verify protected routes redirect to `/login` and `/signup` stays guest-only.
- Verify login works for existing manager/admin accounts and the app bootstrap restores session after reload through refresh cookie.
- Verify auth bootstrap can consume `employee_profile` without needing a second request for basic employee identity.
- Verify signup creates an employee account and lands inside the protected shell with employee role.
- Verify logout clears session and returns the browser to `/login`.
- As manager/admin, verify sidebar navigation exposes `Reference Data`, `Tasks`, `Planning`, and `Assignments`.
- As employee, verify sidebar hides `Reference Data`, `Planning`, and `Assignments`, and instead shows `My Schedule` and `My Leaves`.
- On `Reference Data`, verify manager does not see `users` CRUD and only gets the allowed action set for departments, skills, and employees.
- On departments screens, verify UI assumptions match the new nested employee summary shape and do not require employee email from `GET /api/v1/departments/`.
- On `Tasks`, verify task create uses the authenticated user from `/auth/me` and no longer requires reading `/users/`.
- On `Planning`, verify manager/admin can launch a plan run with period-only scope, optional department filter, and optional selected task subset.
- For single-task planning UX, verify the frontend still uses `POST /api/v1/plan-runs` with `task_ids=[task.id]` instead of inventing a new planner route.
- Verify the planning launch summary shows the returned `plan_run_id`, status, assigned count, and unassigned count after `POST /api/v1/plan-runs`.
- Verify entering a persisted `plan_run_id` reloads the run through `GET /api/v1/plan-runs/{plan_run_id}`.
- Verify the persisted review screen renders proposals, diagnostics, and solver statistics from planner-service.
- Verify only the selected proposal exposes the approval CTA.
- Verify approval sends only `task`, `employee`, `source_plan_run_id`, and optional notes to `POST /api/v1/assignments/approve-proposal/`.
- Verify the approval success state shows the returned final `Assignment` summary from `core-service`.
- Verify the browser does not ask the manager to re-enter assignment dates or planned hours during approval.
- On `Assignments`, verify the read-only list loads persisted records from `GET /api/v1/assignments/`.
- As employee, verify `GET /api/v1/assignments/` only surfaces own assignments.
- Verify assignment filters stay local-only and do not mutate backend state.
- Backend follow-up for the next frontend slice:
  confirm `GET /api/v1/assignments/` now returns employee self-scope data for employee-facing task screens.
- Backend follow-up for the next frontend slice:
  confirm manager/admin can use `POST /api/v1/assignments/manual/` and `POST /api/v1/assignments/{id}/reject/`.
- If browser automation is unavailable in the environment, fall back to a live proxy smoke that still exercises `frontend -> /api|/planner-api -> core/planner` on real services.
- As employee, verify `Tasks` and `Task Requirements` are read-only.
- Backend truth after Stage 1:
  employee `work-schedules` and `work-schedule-days` are read-only through the API.
- Backend truth after Stage 1:
  employee `employee-leaves` can be created freely, but update/delete work only while status is `requested`; manager/admin approval now uses `POST /api/v1/employee-leaves/{id}/set-status/`.
- Backend truth after Stage 1:
  manual final assignment uses `POST /api/v1/assignments/manual/`, and final assignment rejection uses `POST /api/v1/assignments/{id}/reject/`.
- Verify task and leave validation errors from backend are surfaced unchanged.
