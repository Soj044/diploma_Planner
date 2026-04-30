# Frontend Vue Chat Prompt

## Purpose

Use this note before any `frontend-app` task so the agent starts from current backend truth instead of stale Milestone 1 assumptions.

## Current runtime

- `frontend-app` is a Vue 3 + Vite + TypeScript thin client.
- Auth flow uses:
  - `POST /api/v1/auth/signup`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me`
- Access token lives only in browser memory.
- Refresh token lives only in the backend HttpOnly cookie on `/api/v1/auth/*`.
- `core-service` is reached through `/api/v1/*`.
- `planner-service` is reached through `/planner-api/api/v1/*`.

## Current frontend milestone status

- Manager/admin runtime already supports:
  - reference-data CRUD
  - task CRUD
  - task-requirement CRUD
  - persisted plan-run launch
  - persisted proposal review
  - planner proposal approval
  - read-only assignments screen
- Employee runtime already supports:
  - signup
  - guarded routing
  - read-only tasks
  - own schedule UI
  - own leaves UI

## Important Stage 1 backend changes

These backend changes are already implemented in `core-service`, even if the current frontend does not use them yet.

- Auth payloads (`signup`, `login`, `refresh`, `me`) now return richer `employee_profile`:
  - `id`
  - `full_name`
  - `department_id`
  - `position_name`
  - `hire_date`
  - `is_active`
- `GET /api/v1/departments/` now includes nested employee summaries without email:
  - `id`
  - `full_name`
  - `position_name`
- Employee assignments are now available via `GET /api/v1/assignments/` with self-scope filtering.
- Employee schedules are now read-only through the API:
  - `work-schedules`: only `list/retrieve`
  - `work-schedule-days`: only `list/retrieve`
- Employee leaves now follow requested-only mutation rules:
  - create always stores `status=requested`
  - employee can update/delete only requested leaves
  - employee cannot change leave status directly
- Manager/admin leave queue now uses:
  - `GET /api/v1/employee-leaves/` -> requested queue
  - `POST /api/v1/employee-leaves/{id}/set-status/` with `approved|rejected`
- Manager/admin assignments now have explicit backend actions:
  - `POST /api/v1/assignments/manual/`
  - `POST /api/v1/assignments/{id}/reject/`
- Manual assignment creates a final `approved` assignment immediately with:
  - `start_date = task.start_date`
  - `end_date = task.due_date`
  - `source_plan_run_id = null`
- Planner approval and manual assignment share one invariant:
  - do not create a second non-rejected final assignment for the same task.

## Planning boundary

- Do not move planner logic into the browser.
- `planner-service` and `packages/contracts` did not change in this Stage 1 slice.
- Single-task planning for future task-creation UX should keep using the existing planner endpoint:
  - `POST /planner-api/api/v1/plan-runs`
  - send `planning_period_start = task.start_date`
  - send `planning_period_end = task.due_date`
  - send `task_ids = [task.id]`
- Final `Assignment` records are still created only by `core-service`.
- Planner approval must still go through `POST /api/v1/assignments/approve-proposal/`.

## Current frontend debt after Stage 1

- Existing employee schedule screens still assume CRUD, but backend is now read-only.
- Existing employee leave screens still assume broader edit/delete semantics than backend now allows.
- Existing manager/admin screens do not yet expose manual assignment, assignment reject, or leave status queue actions.
- Stage 1 backend is ahead of the current employee frontend UX.
- Any new frontend slice must align the UI to current backend rules before adding extra polish.
