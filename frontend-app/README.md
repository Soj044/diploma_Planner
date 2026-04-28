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
- placeholder screens for planning runs and assignments.

## Local setup

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

## Current Stage 6 coverage

- guest-only `login` and `signup` routes;
- protected app routes with silent refresh bootstrap;
- role-aware navigation for `admin`, `manager`, and `employee`;
- manager/admin-only access to `reference-data`, `planning`, and `assignments`;
- employee-only `my-schedule` and `my-leaves` self-service routes.
