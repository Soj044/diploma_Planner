# Frontend Backlog

## Purpose

Track frontend delivery slices for `frontend-app` without losing scope boundaries against the existing backend MVP.

## Current status

- `2026-04-26`: app shell, router, env config, Vite proxy, and thin API layer completed in PR `#5`.
- `2026-04-27`: point 5 completed for the first practical cut with reference-data CRUD for `users`, `departments`, `skills`, and `employees`.

## Milestone 1 slices

| Order | Slice | Status | Notes |
| --- | --- | --- | --- |
| 1 | App shell and navigation | done | Vue 3 + Vite + TypeScript scaffold, layout, routes, API modules |
| 2 | Reference data CRUD needed before task creation | done | Implemented for `users`, `departments`, `skills`, `employees` |
| 3 | Task creation and task requirements | pending | Must reuse core-service contracts, no browser-side planner rules |
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

- `core-service` still requires authenticated access and there is no dedicated frontend auth flow yet.
- Local MVP currently relies on `VITE_CORE_SERVICE_BASIC_AUTH` for browser access to core-service.
- core-service still has no Swagger/OpenAPI UI, so frontend work relies on serializers/routes and manual contract reading.

## Verification baseline

- `cd frontend-app && npm install`
- `cd frontend-app && npm run type-check`
- `cd frontend-app && npm run build`

## Next expected slice after point 5

- finish task creation and task requirement flow on top of the new reference-data screens.
