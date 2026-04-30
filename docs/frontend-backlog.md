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
- `2026-04-29`: point 7 completed on branch `feature/TASK-00-07-plan-run-launch`; managers/admins can now launch persisted plan runs from the frontend with period, optional department scope, and optional task subset selection.
- `2026-04-29`: point 8 completed on branch `feature/TASK-00-08-proposal-review`; managers/admins can now reload a persisted `plan_run_id` and review proposals, diagnostics, and solver statistics from planner-service.
- `2026-04-29`: point 9 completed on branch `feature/TASK-00-09-manager-approval-flow`; managers/admins can now approve the selected persisted proposal and let `core-service` create the final `Assignment`.
- `2026-04-29`: point 10 completed on branch `feature/TASK-00-06-task-creation-flow`; managers/admins can now inspect final assignments in a read-only screen backed by `GET /api/v1/assignments/`.
- `2026-04-29`: live proxy smoke against real `core-service` and `planner-service` completed on branch `feature/TASK-00-06-task-creation-flow`; manager and employee runtime flows now pass through the frontend proxy boundary.
- `2026-04-29`: frontend dev runtime containerization completed on branch `feature/TASK-00-06-task-creation-flow`; `docker compose up --build` now includes `frontend-app` as a Vite dev container while preserving standalone `npm run dev` as an optional path.
- `2026-04-30`: backend Stage 1 role-contract slice completed on branch `feature/TASK-01-stage1-role-contracts`; frontend now lags the latest backend truth for employee schedules/leaves and for the new manual assignment flow.
- `2026-04-30`: frontend Stage 2 shared shell slice completed on branch `feature/TASK-02-stage2-frontend-shell`; primary navigation moved to a top bar, canonical routes were stabilized, `Profile` became a real thin screen, and frontend service/types caught up with Stage 1 backend contracts.

## Milestone 1 slices

| Order | Slice | Status | Notes |
| --- | --- | --- | --- |
| 1 | App shell and navigation | done | Vue 3 + Vite + TypeScript scaffold, layout, routes, API modules |
| 2 | Reference data CRUD needed before task creation | done | Implemented for `users`, `departments`, `skills`, `employees` |
| 3 | Task creation and task requirements | done | Implemented for `tasks` and `task-requirements` with linked selection flow |
| 4 | Plan run launch | done | Manager/admin launch form uses `POST /api/v1/plan-runs` with auth-derived initiator |
| 5 | Proposal and diagnostics review | done | Persisted review screen reads `GET /api/v1/plan-runs/{plan_run_id}` and renders proposals, diagnostics, and solver stats |
| 6 | Final assignment approval | done | Approval now happens from the `Planning` persisted review screen via `/assignments/approve-proposal/` |
| 7 | Assignments read-only view | done | Frontend now reads final assignments from `/api/v1/assignments/` with local-only filters |

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

## Backend Stage 1 contract delta

- Auth payloads (`signup`, `login`, `refresh`, `me`) now return `employee_profile` with `id`, `full_name`, `department_id`, `position_name`, `hire_date`, and `is_active`.
- `GET /api/v1/departments/` now includes nested employee summaries with `id`, `full_name`, and `position_name`; this nested read model intentionally omits employee email.
- Employee `work-schedules` and `work-schedule-days` are now self-scope read-only with `list/retrieve` only.
- Employee leaves now follow a request/review contract:
  - employee create always stores `requested`;
  - employee can update/delete only own `requested` leaves;
  - employee cannot change leave status directly;
  - manager/admin process the queue through `POST /api/v1/employee-leaves/{id}/set-status/`.
- Final assignment now has two backend paths:
  - planner approval through `/assignments/approve-proposal/`;
  - manual assignment through `/assignments/manual/`.
- Manual assignment creates a final `approved` assignment with `start_date=task.start_date`, `end_date=task.due_date`, and `source_plan_run_id=null`.
- Planner approval and manual assignment share the same invariant: no second non-rejected final assignment for one task.
- `planner-service` and `packages/contracts` did not change in this slice; single-task planning still reuses `POST /api/v1/plan-runs` with `task_ids=[task.id]`.

## Known frontend gaps

- core-service still has no Swagger/OpenAPI UI, so frontend work relies on serializers/routes and manual contract reading.
- In the current agent environment, true headless browser access to `127.0.0.1:5173` timed out, so the final live smoke was executed through the real frontend proxy boundary from inside `frontend-smoke` rather than by DOM-level browser automation.
- Current employee frontend screens still assume schedule CRUD and broader leave editing than the Stage 1 backend now allows.
- Current manager/admin frontend screens do not yet expose `POST /api/v1/assignments/manual/`, `POST /api/v1/assignments/{id}/reject/`, or the requested-leave status queue action.
- Stage 2 shell now uses the richer `employee_profile` for session and `/profile`, but the canonical `departments`, `schedule`, and `leaves` routes are still scaffold screens waiting for domain UI in the next slice.

## Verification baseline

- `cd frontend-app && npm install`
- `cd frontend-app && npm run type-check`
- `cd frontend-app && npm run build`

## Stage 6 progress

- Merge status: Stage 6 auth migration is already merged into `feature/TASK-00-06-task-creation-flow`
- Completed:
  - Stage 1: runtime and dev proxy realignment
  - Stage 2: auth foundation and session lifecycle
  - Stage 3: role-aware navigation and route guards
  - Stage 4: RBAC migration for existing screens
  - Stage 5: employee self-service and final docs pass
  - Stage 6 auth migration complete

## Next expected slice after point 10 and Stage 2 shell

- Frontend Milestone 1 is complete, Stage 1 backend contracts are in place, and the Stage 2 shell now exposes the final route skeleton; the next slice should build the real role-specific screens behind those URLs.
- Recommended Stage 3 follow-up:
  - switch employee task screen from global `tasks` listing to employee-scoped `assignments` view enriched with task metadata;
  - convert employee schedule screens to read-only;
  - convert employee leaves flow to requested-only editing;
  - add manager/admin leave queue actions via `set-status`;
  - render the departments directory from nested employee summaries;
  - add manager/admin manual assignment and reject flows on top of the new core-service endpoints;
  - keep single-task planning on the existing `POST /api/v1/plan-runs` contract with `task_ids=[task.id]`.
