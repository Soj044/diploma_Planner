# frontend-app

Vue 3 + Vite + TypeScript shell for the Workestrator MVP frontend.

## Scope of the first slice

- application scaffold and routing;
- thin API layer for `core-service` and `planner-service`;
- local Vite proxy for backend calls during development;
- token-based auth flow with login, signup, refresh, logout, and me bootstrap;
- role-aware navigation and guarded routes;
- live CRUD for `users`, `departments`, `skills`, and `employees`;
- live task CRUD and task-requirement CRUD;
- employee self-service CRUD for own work schedules, schedule days, and leaves;
- live planning run launch, persisted proposal review, and manager approval handoff;
- live read-only assignments screen backed by `core-service`.

## Local setup

### Option 1: Docker Compose dev runtime

From the repository root:

```bash
docker compose up --build frontend-app
```

This starts the Vite dev server inside the `frontend-app` container and proxies:

- `/api/*` -> `core-service`
- `/planner-api/*` -> `planner-service`

Frontend becomes available at `http://localhost:5173`.

### Option 2: Standalone Vite on the host

```bash
cd frontend-app
cp .env.example .env.local
npm install
npm run dev
```

## Environment

- `VITE_CORE_SERVICE_URL` defaults to `/api/v1`
- `VITE_PLANNER_SERVICE_URL` defaults to `/planner-api/api/v1`
- `VITE_CORE_SERVICE_PROXY_TARGET` defaults to `http://localhost:8000`
- `VITE_PLANNER_SERVICE_PROXY_TARGET` defaults to `http://localhost:8001`
- in `docker compose`, proxy targets are overridden to `http://core-service:8000` and `http://planner-service:8001`

## Runtime routing

- `core-service` should be reached through `/api/v1/*`
- auth endpoints should be reached through `/api/v1/auth/*`
- Vite proxies `/api` directly to `core-service` without path rewrite so the refresh cookie path `/api/v1/auth/` still matches
- `planner-service` is reached through `/planner-api/api/v1/*`
- Vite rewrites `/planner-api/*` to backend root before forwarding to planner-service

## Current auth flow

- `signup`, `login`, `refresh`, `logout`, and `me` are called against `core-service`
- refresh token stays in an HttpOnly cookie managed by backend
- access token stays only in in-memory frontend state
- app bootstrap tries `refresh -> me` before protected routes become available
- protected API calls retry once after a `401` by attempting silent refresh

## Current point 5 coverage

- list, create, edit, delete users;
- list, create, edit, delete departments;
- list, create, edit, delete skills;
- list, create, edit, delete employees;
- explicitly defer employee skills and availability overrides to a later slice.

## Current point 6 coverage

- list, create, edit, delete tasks;
- list, create, edit, delete task requirements;
- focus task requirements from a selected task in the same screen;
- create tasks with `created_by_user = me.id`;
- keep employee task visibility read-only.

## Current point 7 coverage

- launch persisted plan runs from the `Planning` screen;
- collect `planning_period_start`, `planning_period_end`, optional `department_id`, and optional `task_ids`;
- derive `initiated_by_user_id` from the authenticated manager/admin session;
- show immediate run summary after `POST /api/v1/plan-runs`;
- intentionally defer full proposal and diagnostics review to the next slice.

## Current point 8 coverage

- reload persisted plan runs by `plan_run_id` from the same `Planning` screen;
- render proposal list with task/employee labels, score, rank, selected marker, timing, and explanation text;
- render unassigned task diagnostics and persisted solver statistics;
- keep planner artifacts read-only even while enabling separate approval handoff.

## Current point 9 coverage

- approve the selected persisted proposal from the `Planning` screen;
- send only `task`, `employee`, `source_plan_run_id`, and optional `notes` to `POST /api/v1/assignments/approve-proposal/`;
- show the created final `Assignment` summary returned by `core-service`;
- keep final assignments creation authority in `core-service`.

## Current point 10 coverage

- read final assignments directly from `GET /api/v1/assignments/`;
- show task and employee labels alongside persisted assignment timing and notes;
- keep the screen read-only with only local UX filters, not frontend-owned business state.

## Current milestone status

- frontend milestone 1 is functionally complete;
- manager flow now covers task creation, plan run launch, persisted proposal review, approval, and read-only assignments;
- employee flow covers signup, guarded routing, own schedules, own schedule days, and own leaves.

## Current Stage 6 coverage

- guest-only `login` and `signup` routes;
- protected app routes with silent refresh bootstrap;
- role-aware navigation for `admin`, `manager`, and `employee`;
- manager/admin-only access to `reference-data`, `planning`, and `assignments`;
- employee-only `my-schedule` and `my-leaves` self-service routes.
