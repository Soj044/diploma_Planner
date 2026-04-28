# Frontend Backlog

## Purpose

Track frontend delivery slices for `frontend-app` without losing scope boundaries against the existing backend MVP.

## Current status

- `2026-04-26`: app shell, router, env config, Vite proxy, and thin API layer completed in PR `#5`.
- `2026-04-27`: point 5 completed for the first practical cut with reference-data CRUD for `users`, `departments`, `skills`, and `employees`.
- `2026-04-27`: point 6 completed with task CRUD and task-requirement CRUD linked through the Tasks screen.
- `2026-04-28`: Stage 6 / Stage 1 completed on branch `feature/TASK-06-01-frontend-token-auth`; runtime moved away from Basic auth and dev proxy was realigned for `/api/v1/auth/*` refresh-cookie compatibility.
- `2026-04-28`: Stage 6 / Stage 2 completed on branch `feature/TASK-06-01-frontend-token-auth`; frontend now has token auth screens, in-memory access token state, silent refresh bootstrap, and guarded routes.
- `2026-04-28`: Stage 6 / Stage 3 completed on branch `feature/TASK-06-02-frontend-rbac-self-service`; navigation and route access now react to backend roles, and employee-only self-service routes were reserved.
- `2026-04-28`: Stage 6 / Stage 4 completed on branch `feature/TASK-06-02-frontend-rbac-self-service`; existing reference-data and task screens were pruned so frontend no longer advertises actions that backend RBAC will reject.
- `2026-04-28`: Stage 6 / Stage 5 completed on branch `feature/TASK-06-02-frontend-rbac-self-service`; employee self-service CRUD for schedules, schedule days, and leaves is now live, and frontend docs were updated to the token-auth runtime.

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
- `availability-overrides`

Reason: `work-schedules`, `work-schedule-days`, and `employee-leaves` were intentionally deferred from the first reference-data route and later delivered as employee self-service screens during Stage 6 auth migration.

## Known frontend gaps

- Planning run launch UI is still pending on top of the new auth and RBAC foundation.
- Proposal review, assignment approval, and final assignments read-only screens are still pending.
- core-service still has no Swagger/OpenAPI UI, so frontend work relies on serializers/routes and manual contract reading.

## Verification baseline

- `cd frontend-app && npm install`
- `cd frontend-app && npm run type-check`
- `cd frontend-app && npm run build`

## Stage 6 progress

- Active branch: `feature/TASK-06-02-frontend-rbac-self-service`
- Active PR: PR `#9` covers stages 1-2; stacked PR for stages 3-5 will be opened after final verification
- Completed:
  - Stage 1: runtime and dev proxy realignment
  - Stage 2: auth foundation and session lifecycle
  - Stage 3: role-aware navigation and route guards
  - Stage 4: RBAC migration for existing screens
  - Stage 5: employee self-service and final docs pass
- Next expected stage:
  - Stage 6 auth migration complete

## Next expected slice after point 6

- implement plan run launch and proposal review on top of the new token-auth and RBAC foundation.
