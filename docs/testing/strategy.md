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
- ai-layer runtime/bootstrap, retrieval sync, structured explanations, and shared pgvector foundation
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
- ai-layer: containerized startup, `/health` probe, authenticated `/api/v1/capabilities`, authenticated explanation routes, PostgreSQL connectivity bootstrap, `CREATE EXTENSION vector`, isolated `ai_layer` schema creation without touching core/planner truth tables, repository creation of `index_items`/`sync_state`/`explanation_logs`, HNSW cosine index creation, full/incremental sync, delete-path handling, stale-index fallback, and structured Ollama output validation
- internal AI helper routes:
  - `core-service`: `service-boundary`, `index-feed`, `assignment-context`
  - `planner-service`: `service-boundary`, `index-feed`, `proposal-context`, `unassigned-context`
  - all accept only `X-Internal-Service-Token`
- frontend-app: install dependencies, type-check the Vue shell, build production bundle, verify containerized Vite startup via `docker compose`, and manually verify token auth, guarded routing, employee canonical routes, manager/admin `/tasks/new` flow, and hidden advanced routes
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

# AI layer
cd services/ai-layer
poetry install
poetry run pytest -q
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8002
poetry run python -m app.cli.reindex --mode full

# Frontend app
cd frontend-app
npm install
npm run type-check
npm run build

# Container smoke
cd /path/to/repo
docker compose up --build

# AI foundation smoke
curl http://localhost:8002/health
curl -H "Authorization: Bearer <manager-or-admin-access-token>" http://localhost:8002/api/v1/capabilities
curl -X POST -H "Authorization: Bearer <manager-or-admin-access-token>" -H "Content-Type: application/json" \
  -d '{"task_id":"1","employee_id":"1","plan_run_id":"1"}' \
  http://localhost:8002/api/v1/explanations/assignment-rationale
docker exec workestrator-postgres psql -U workestrator -d workestrator -c '\dx vector'
docker exec workestrator-postgres psql -U workestrator -d workestrator -c '\dn'
docker exec workestrator-postgres psql -U workestrator -d workestrator -c '\d ai_layer.index_items'

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
- Verify `POST /api/v1/assignments/approve-proposal/` creates a final `approved` assignment, keeps planner handoff semantics, and moves `Task.status` to `assigned`.
- Verify `POST /api/v1/assignments/manual/` moves `Task.status` to `assigned`.
- Verify `POST /api/v1/assignments/{id}/reject/` marks the final assignment as rejected, reopens `Task.status` to `planned`, and allows a future non-rejected final assignment.
- Verify planner approval and manual assignment both reject creation of a second non-rejected final assignment for the same task.
- Verify single-task planning still uses the existing planner boundary `POST /api/v1/plan-runs` with `task_ids=[task.id]`.
- Verify planner-backed final assignment keeps `end_date == task.due_date` for date-based tasks.

## Frontend Manual Smoke

- Preferred runtime: `docker compose up --build` from the repository root.
- Optional alternative: start backend in Docker and run `frontend-app` on the host with `npm run dev`.
- Start backend services and the frontend shell locally.
- In the current cycle, optionally verify that `/ai-api` is reserved in Vite runtime even though no user-facing AI UI is wired yet.
- Verify `ai-layer` returns `401` without Bearer auth, `403` for `employee`, and `200` for `manager|admin` on `/api/v1/capabilities`.
- Verify `ai-layer` explanation routes return `503` with `AI retrieval index is not ready.` until the retrieval index is populated.
- Run `poetry run python -m app.cli.reindex --mode full` in `services/ai-layer`, then verify explanation routes can return `200`.
- Verify `GET /api/v1/internal/ai/service-boundary/`, `GET /api/v1/internal/ai/index-feed/`, and `GET /api/v1/internal/ai/tasks/{task_id}/assignment-context/` in `core-service` reject missing internal token and accept the shared token.
- Verify `GET /api/v1/internal/ai/service-boundary`, `GET /api/v1/internal/ai/index-feed`, `GET /api/v1/internal/ai/plan-runs/{plan_run_id}/proposal-context`, and `GET /api/v1/internal/ai/plan-runs/{plan_run_id}/unassigned-context` in `planner-service` reject missing internal token and accept the shared token.
- Verify `assignment-rationale` explanations use live task/employee context plus retrieved `assignment_case` history, while `unassigned-task` explanations use persisted diagnostic context plus retrieved `unassigned_case` history.
- Verify stopping `ollama` causes explanation routes to degrade with controlled `503`, not broken approval/manual assignment flows.
- Before planner-dependent checks, prepare two task datasets:
  - a positive planner case with eligible employee skills and an availability slot that covers the whole date-based task window so `/tasks/new` can surface a selected proposal;
  - a manual fallback case with no eligible employee so `/tasks/new` opens manual assignment mode directly.
- Before manager/admin leave checks, ensure at least one employee has a `requested` leave record.
- Before manager/admin schedule checks, ensure at least one employee exists for the `/schedule` workspace.
- Open `http://localhost:5173`.
- As anonymous user, verify protected routes redirect to `/login` and `/signup` stays guest-only.
- After authentication, verify `/` redirects to `/tasks`.
- Verify login works for existing manager/admin accounts and the app bootstrap restores session after reload through refresh cookie.
- Verify auth bootstrap can consume `employee_profile` without needing a second request for basic employee identity.
- Verify signup creates an employee account and lands inside the protected shell with employee role.
- Verify logout clears session and returns the browser to `/login`.
- As `employee`, verify the top navigation shows exactly `Tasks`, `Schedule`, `Leaves`, `Departments`, and `Profile`.
- As `manager`, verify the top navigation shows exactly `Tasks`, `Schedule`, `Leaves`, `Departments`, and `Profile`.
- As `admin`, verify the top navigation additionally shows `Admin`.
- Verify `/reference-data` redirects to `/admin`, `/my-schedule` redirects to `/schedule`, and `/my-leaves` redirects to `/leaves`.
- Verify `/planning` and `/assignments` remain reachable by direct URL for `manager` and `admin`, even though they are hidden from the primary navigation.
- Verify `/tasks/new` is reachable only for `manager` and `admin`.
- On `/admin`, verify the reference-data workspace still loads, preserves role-aware CRUD gating, and exposes the admin-only users/roles workspace.
- On `/departments`, verify the directory renders nested employee summaries and does not require employee email from `GET /api/v1/departments/`.
- As employee, verify `/tasks` is assignment-first and shows deadline from `assignment.end_date`, plus title/description/department/status from joined task data.
- As employee, verify `/schedule` is read-only and exposes no create/edit/delete controls.
- As employee, verify `/leaves` shows all leave records, opens a create form without a writable `status` field, and exposes edit/delete only while status is `requested`.
- As manager/admin, verify `/schedule` loads a cross-employee workspace rather than the employee read-only view.
- As manager/admin, verify `/schedule` lets the operator choose an employee, create a schedule, edit a schedule, delete a schedule, and keep default-schedule selection visible.
- As manager/admin, verify `/schedule` lets the operator create, edit, and delete weekday rules for the selected schedule.
- As manager/admin, verify non-working weekday rules are persisted without editable time inputs in the browser.
- As manager/admin, verify `/leaves` shows only requested records, resolves employee names/positions from `GET /api/v1/employees/`, and never exposes date/type/comment editing controls.
- As manager/admin, verify `/leaves` `Approve` and `Reject` both call the status-only action and remove the decided record from the queue after reload.
- On `/tasks`, verify manager/admin see only tasks where `created_by_user === currentUser.id`.
- On `/tasks/new`, verify task create uses the authenticated user from `/auth/me` and no longer requires reading `/users/`.
- On `/tasks/new`, verify `Save task` persists the task without planner launch.
- On `/tasks/new`, verify `Save + Assignment` requires `status=planned`, `start_date`, and `due_date`.
- On `Planning`, verify manager/admin can launch a plan run with period-only scope, optional department filter, and optional selected task subset.
- For single-task planning UX, verify `/tasks/new` still uses `POST /api/v1/plan-runs` with `task_ids=[task.id]` instead of inventing a new planner route.
- Verify the planning launch summary shows the returned `plan_run_id`, status, assigned count, and unassigned count after `POST /api/v1/plan-runs`.
- Verify entering a persisted `plan_run_id` reloads the run through `GET /api/v1/plan-runs/{plan_run_id}`.
- Verify the persisted review screen still renders proposals, diagnostics, and solver statistics from planner-service.
- On `/tasks/new`, verify a selected proposal opens the planner suggestion modal, and no-candidate diagnostics open manual assignment mode.
- Verify planner suggestion approval sends only `task`, `employee`, and `source_plan_run_id` to `POST /api/v1/assignments/approve-proposal/`.
- Verify manual assignment sends `task`, `employee`, `planned_hours`, and optional `notes` to `POST /api/v1/assignments/manual/`.
- Verify the browser never invents assignment dates and always displays task-backed dates in manual mode.
- On `Assignments`, verify the read-only list loads persisted records from `GET /api/v1/assignments/`.
- As employee, verify `GET /api/v1/assignments/` only surfaces own assignments.
- Verify assignment filters stay local-only and do not mutate backend state.
- On `/profile`, verify the screen renders `email`, `role`, `full_name`, `department_id`, `position_name`, `hire_date`, and `is_active` directly from the auth session payload.
- If browser automation is unavailable in the environment, fall back to a live proxy smoke that still exercises `frontend -> /api|/planner-api -> core/planner` on real services.
- As employee, verify task requirements are no longer exposed as a writable concept on the canonical `/tasks` route.
- Backend truth after Stage 3/4:
  employee `work-schedules` and `work-schedule-days` are read-only through the API and through the canonical `/schedule` route.
- Backend truth after Stage 3/4:
  employee `employee-leaves` can be created freely, but update/delete work only while status is `requested`.
- Backend truth after Stage 4 completion:
  manager/admin `/schedule` is the operational CRUD workspace for any employee schedule and weekday rule.
- Backend truth after Stage 4 completion:
  manager/admin `/leaves` is the requested-only review queue powered by `POST /api/v1/employee-leaves/{id}/set-status/`.
- Backend truth after Stage 3/4:
  manual final assignment uses `POST /api/v1/assignments/manual/`, planner approval uses `POST /api/v1/assignments/approve-proposal/`, and both sync the task into `assigned`.
- Verify task and leave validation errors from backend are surfaced unchanged.
