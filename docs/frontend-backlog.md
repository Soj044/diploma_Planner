# Frontend Backlog

## Purpose

Track frontend delivery slices for `frontend-app` without losing scope boundaries against the existing backend MVP.

## Current status

- `2026-04-26`: app shell, router, env config, Vite proxy, and thin API layer completed in PR `#5`.
- `2026-04-27`: point 5 completed for the first practical cut with reference-data CRUD for `users`, `departments`, `skills`, and `employees`.
- `2026-04-27`: point 6 completed with task CRUD and task-requirement CRUD linked through the Tasks screen.
- `2026-04-28`: Stage 6 / Stage 1 completed on branch `feature/TASK-06-01-frontend-token-auth`; runtime moved away from Basic auth and dev proxy was realigned for `/api/v1/auth/*` refresh-cookie compatibility.

## Milestone 1 slices

| Order | Slice | Status | Notes |
| --- | --- | --- | --- |
| 1 | App shell and navigation | done | Vue 3 + Vite + TypeScript scaffold, layout, routes, API modules |
| 2 | Reference data CRUD needed before task creation | done | Implemented for `users`, `departments`, `skills`, `employees` |
| 3 | Task creation and task requirements | done | Implemented for `tasks` and `task-requirements` with linked selection flow |
| 4 | Plan run launch | pending | Use `POST /api/v1/plan-runs` only |
| 5 | Proposal and diagnostics review | pending | Read persisted planner artifacts via `GET /api/v1/plan-runs/{plan_run_id}` |
| 6 | Final assignment approval | pending | Handoff only `task + employee + source_plan_run_id` to core-service |
| 7 | Assignments read-only view | pending | Final business truth comes from `/api/v1/assignments/` |

## Point 5 scope decision

The current implementation cut for point 5 treats the following entities as the minimal reference-data subset required before task creation becomes useful:

- `users`
- `departments`
- `skills`
- `employees`

Deferred planning-facing reference entities for later slices:

- `employee-skills`
- `work-schedules`
- `work-schedule-days`
- `employee-leaves`
- `availability-overrides`

Reason: they are needed before planning quality and availability logic, but not before the first task and task-requirement screens.

## Known frontend gaps

- Frontend runtime is aligned to token auth, but login/signup/refresh/logout/me screens and state management are not wired yet.
- Route guards, role-aware navigation, and employee self-service screens are still missing.
- core-service still has no Swagger/OpenAPI UI, so frontend work relies on serializers/routes and manual contract reading.

## Verification baseline

- `cd frontend-app && npm install`
- `cd frontend-app && npm run type-check`
- `cd frontend-app && npm run build`

## Stage 6 progress

- Active branch: `feature/TASK-06-01-frontend-token-auth`
- Active PR: not opened yet
- Completed:
  - Stage 1: runtime and dev proxy realignment
- Next expected stage:
  - Stage 2: auth foundation and session lifecycle

## Next expected slice after point 6

- implement plan run launch on top of the new task and task-requirement screens.
