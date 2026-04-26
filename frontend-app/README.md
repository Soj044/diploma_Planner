# frontend-app

Vue 3 + Vite + TypeScript shell for the Workestrator MVP frontend.

## Scope of the first slice

- application scaffold and routing;
- thin API layer for `core-service` and `planner-service`;
- local Vite proxy for backend calls during development;
- placeholder screens for reference data, tasks, planning runs, and assignments.

## Local setup

```bash
cd frontend-app
cp .env.example .env.local
npm install
npm run dev
```

## Environment

- `VITE_CORE_SERVICE_URL` defaults to `/core-api/api/v1`
- `VITE_PLANNER_SERVICE_URL` defaults to `/planner-api/api/v1`
- `VITE_CORE_SERVICE_PROXY_TARGET` defaults to `http://localhost:8000`
- `VITE_PLANNER_SERVICE_PROXY_TARGET` defaults to `http://localhost:8001`
- `VITE_CORE_SERVICE_BASIC_AUTH` is an explicit local MVP workaround until a real frontend auth flow exists

## Current auth assumption

`core-service` requires authenticated access. This first frontend slice does not add a dedicated login flow yet.
For local MVP use, the shell can send HTTP Basic credentials through `VITE_CORE_SERVICE_BASIC_AUTH`.
This is acceptable only for local development and must be replaced by a proper auth flow later.
