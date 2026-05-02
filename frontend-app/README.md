# frontend-app

Vue 3 + Vite + TypeScript shell for the Workestrator MVP frontend.

## Current frontend slice

- application scaffold and routing;
- thin API layer for `core-service` and `planner-service`;
- local Vite proxy for backend calls during development;
- token-based auth flow with login, signup, refresh, logout, and me bootstrap;
- top navigation shell with role-aware primary routes and guarded access;
- live CRUD for `users`, `departments`, `skills`, and `employees`;
- employee-facing assignment inbox, read-only schedule, requested-only leaves, and department directory;
- manager/admin owned task workspace on `/tasks` and create-and-assign flow on `/tasks/new`;
- live task-requirement CRUD;
- live planning run launch, persisted proposal review, and manager approval handoff;
- live read-only assignments screen backed by `core-service`.
- canonical employee routes for `schedule`, `leaves`, `departments`, and `profile`;
- hidden compatibility routes for `planning`, `assignments`, `reference-data`, `my-schedule`, and `my-leaves`.

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

## Current route map

- guest-only routes:
  - `/login`
  - `/signup`
- protected canonical routes:
  - `/tasks`
  - `/tasks/new` for `manager` and `admin`
  - `/schedule`
  - `/leaves`
  - `/departments`
  - `/profile`
  - `/admin` for `admin` only
- protected advanced routes kept for compatibility:
  - `/planning` for `manager` and `admin`
  - `/assignments` for `manager` and `admin`
- redirects:
  - `/` -> `/tasks`
  - `/reference-data` -> `/admin`
  - `/my-schedule` -> `/schedule`
  - `/my-leaves` -> `/leaves`

## Current point 5 coverage

- list, create, edit, delete users;
- list, create, edit, delete departments;
- list, create, edit, delete skills;
- list, create, edit, delete employees;
- explicitly defer employee skills and availability overrides to a later slice.

## Current task coverage

- employee `/tasks` now reads self-scoped assignments and joins them with task and department labels;
- manager/admin `/tasks` now shows only tasks created by the current authenticated user;
- `/tasks/new` saves a task first, then can continue into the single-task assignment flow;
- task requirements stay editable for manager/admin users after the task is saved;
- single-task assignment still reuses persisted planner runs plus backend approval/manual assignment endpoints.

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
- employee canonical routes now render real assignment, schedule, leave, department, and profile UX on top of Stage 1 backend contracts;
- manager/admin flow now splits into an owned task workspace on `/tasks` and a dedicated create-and-assign flow on `/tasks/new`;
- `planning` and `assignments` remain available as advanced compatibility routes for persisted review and audit.

## Current shell coverage

- guest-only `login` and `signup` routes;
- protected app routes with silent refresh bootstrap;
- top navigation for `admin`, `manager`, and `employee`;
- canonical protected routes for `tasks`, `schedule`, `leaves`, `departments`, `profile`, and `admin`;
- hidden advanced routes for `planning` and `assignments`;
- compatibility redirects from `reference-data`, `my-schedule`, and `my-leaves`.
