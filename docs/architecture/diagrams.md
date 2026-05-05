# Architecture Diagrams

## Editable Draw.io Files

- [class-diagram.drawio](/home/oleg/PycharmProjects/Workestrator/docs/architecture/class-diagram.drawio)
- [task-creation-and-final-assignment-flow.drawio](/home/oleg/PycharmProjects/Workestrator/docs/architecture/task-creation-and-final-assignment-flow.drawio)
- [employee-selection-algorithm.drawio](/home/oleg/PycharmProjects/Workestrator/docs/architecture/employee-selection-algorithm.drawio)

## High-Level Service Flow (MVP)

```text
manager -> frontend-app: navigate top-nav tasks/schedule/leaves/departments/profile, use /tasks/new as primary create-and-assign path, plus hidden planning/assignments advanced routes
employee -> frontend-app: navigate top-nav tasks/schedule/leaves/departments/profile routes backed by assignment-first tasks and read-only self-service screens
frontend-app -> core-service: create/update employees, skills, tasks, work schedules, weekday rules, leave decisions, and assignment actions
frontend-app -> core-service: login/signup/refresh/me (employee_profile included) + employee schedule/leave/assignment reads
frontend-app -> core-service: GET /api/v1/departments/ (nested employee summaries)
frontend-app -> planner-service: POST /api/v1/plan-runs (single-task flow uses task_ids=[task.id] from /tasks/new)
frontend-app runtime: reserves /ai-api for future ai-layer explanation routes
planner-service -> core-service: POST /api/v1/planning-snapshot/ + X-Internal-Service-Token
planner-service (CP-SAT): eligibility -> scoring -> optimization
planner-service -> planner artifact store: save run + snapshot + proposals + diagnostics
planner-service -> frontend-app: assignment proposals + diagnostics
frontend-app -> planner-service: GET /api/v1/plan-runs/{id}
frontend-app -> core-service: POST /api/v1/assignments/approve-proposal/
frontend-app -> core-service: POST /api/v1/assignments/manual/ or POST /api/v1/assignments/{id}/reject/
frontend-app -> core-service: POST /api/v1/employee-leaves/{id}/set-status/ (manager/admin)
core-service -> planner-service: GET /api/v1/plan-runs/{id} + X-Internal-Service-Token
ai-layer -> postgres: bootstrap vector extension + ai_layer schema for derived AI storage
ai-layer -> ollama: future local chat/embedding calls
core-service -> core database: store final assignments, sync task status, and persist leave status changes
```

## Approval Handoff

```text
manager -> planner-service: review proposal
manager -> core-service: POST /api/v1/assignments/approve-proposal/
core-service -> planner-service: GET /api/v1/plan-runs/{id} + X-Internal-Service-Token
core-service: validate run status + proposal pair + idempotency
core-service -> core database: create approved Assignment + AssignmentChangeLog
planner-service: keeps proposal immutable as planning artifact only

manager/admin -> core-service: POST /api/v1/assignments/manual/
core-service: copy start_date from task.start_date
core-service: copy end_date from task.due_date
core-service: set source_plan_run_id = null
core-service: validate final-assignment invariant + sync task.status to assigned
core-service -> core database: create approved Assignment + AssignmentChangeLog

manager/admin -> core-service: POST /api/v1/assignments/{id}/reject/
core-service -> core database: mark Assignment rejected + write AssignmentChangeLog + reopen task.status to planned
```

## Runtime Diagram (Docker)

```text
browser
  |
  v
+---------------------+
|    frontend-app     |
|  vue + vite dev     |
| docker compose svc  |
|       :5173         |
+----------+----------+
           | /api, /planner-api, /ai-api (reserved)
           v
+---------------------+      +-----------------------------+
|   core-service      |<---->|          postgres           |
|   django + drf      |      | pgvector + core db +        |
+----------+----------+      | ai_layer schema foundation  |
           ^                 +-----------------------------+
           | POST /api/v1/planning-snapshot/
           | X-Internal-Service-Token
           |
           |
+---------------------+      +-----------------------+
|   planner-service   |----->|   planner sqlite db   |
|  fastapi + or-tools |      |   planner.sqlite3     |
+---------------------+      +-----------------------+

+---------------------+      +-----------------------+
|      ai-layer       |----->|        ollama         |
|  fastapi bootstrap  |      | local model runtime   |
|       :8002         |      |        :11434         |
+----------+----------+      +-----------------------+
           |
           v
      postgres ai_layer bootstrap
      - CREATE EXTENSION vector
      - CREATE SCHEMA ai_layer
```

`frontend-app` can also be run standalone on the host with `npm run dev`, but `docker compose up --build` is now the default full-stack dev runtime.
`ai-layer` runtime is available in compose now, but no frontend AI UX or retrieval API is wired in this cycle.

## Frontend-Useful Read Models (Stage 1)

```text
auth payloads:
  POST /api/v1/auth/login
  POST /api/v1/auth/signup
  POST /api/v1/auth/refresh
  GET  /api/v1/auth/me

  include employee_profile:
    id, full_name, department_id, position_name, hire_date, is_active

departments list:
  GET /api/v1/departments/

  includes nested employees:
    id, full_name, position_name

  does not include nested employee email
```

## Frontend Boundary

```text
frontend-app:
  routes:
    login, signup, shell, tasks, tasks/new, schedule, leaves, departments, profile, admin
    hidden advanced routes: planning, assignments
    compatibility redirects: reference-data -> admin, my-schedule -> schedule, my-leaves -> leaves

  client modules:
    services/auth-service.ts
    services/core-service.ts
    services/planner-service.ts
    services/http.ts
    composables/useAuth.ts

  rules:
    no planner eligibility/scoring logic in browser
    no frontend-owned business truth
    token auth via core-service (access bearer + refresh cookie)
    frontend must follow backend-owned role and lifecycle rules for assignments, schedules, and leaves

  canonical role split:
    /schedule = employee read-only view, manager/admin cross-employee CRUD workspace
    /leaves = employee requested-only self-service, manager/admin requested review queue
```

## Auth Flow (MVP)

```text
frontend-app -> core-service: POST /api/v1/auth/login
core-service -> frontend-app: access token (JSON) + refresh token (HttpOnly cookie) + employee_profile
frontend-app -> core-service: POST /api/v1/auth/refresh on app bootstrap
frontend-app -> core-service: GET /api/v1/auth/me (Authorization: Bearer <access>)
core-service -> frontend-app: me payload with role + employee_profile
frontend-app -> core-service: POST /api/v1/auth/refresh (refresh cookie)
core-service -> frontend-app: rotated refresh cookie + new access token + employee_profile
frontend-app -> planner-service: Authorization: Bearer <access>
planner-service -> core-service: POST /api/v1/auth/introspect + X-Internal-Service-Token
core-service -> planner-service: user_id + role + is_active + employee_id
core-service -> planner-service: persisted approval reread via X-Internal-Service-Token
```

## Leave Review Boundary

```text
employee -> core-service: POST /api/v1/employee-leaves/ (status forced to requested)
employee -> core-service: PATCH/DELETE own requested leave only
employee -> core-service: cannot set leave status directly
manager/admin -> frontend-app: canonical /leaves route shows requested queue only
manager/admin -> core-service: GET /api/v1/employee-leaves/ (requested queue visible)
manager/admin -> core-service: POST /api/v1/employee-leaves/{id}/set-status/ approved|rejected
```

## Schedule Management Boundary

```text
employee -> core-service: GET /api/v1/work-schedules/ + GET /api/v1/work-schedule-days/ (self-scope read-only)
manager/admin -> frontend-app: canonical /schedule route selects employee + schedule
manager/admin -> core-service: GET /api/v1/employees/
manager/admin -> core-service: GET/POST/PATCH/DELETE /api/v1/work-schedules/
manager/admin -> core-service: GET/POST/PATCH/DELETE /api/v1/work-schedule-days/
frontend-app: joins schedules with weekday rules locally, but keeps schedule truth in core-service
```

## RBAC Boundary (Core-Service)

```text
admin:
  full access to users + operations CRUD + approval

manager:
  operational access (tasks/schedules/overrides/approval) with restricted destructive paths
  leave approval queue via status-only action
  manual final assignment creation and assignment rejection

employee:
  read-only tasks + self-scope assignment reads
  own schedules and schedule days read-only
  own leaves create/update/delete only while status is requested
  no direct leave status mutation

planning snapshot:
  internal-only, requires X-Internal-Service-Token
```

## Data Ownership

```text
core-service:
  users app:
    User

  operations app:
    Department, Employee, Skill, EmployeeSkill,
    WorkSchedule, WorkScheduleDay, EmployeeLeave,
    EmployeeAvailabilityOverride, Task, TaskRequirement,
    Assignment, AssignmentChangeLog

planner-service:
  PlanRun, PlanInputSnapshot, CandidateEligibility,
  CandidateScore, AssignmentProposal, UnassignedTask,
  ConstraintViolation, SolverStatistics

MVP runtime storage:
  SQLite-backed planner artifact repository
  Current persisted slice:
    plan_runs, plan_input_snapshots, assignment_proposals,
    unassigned_tasks, solver_statistics
```

## Core Model Boundary

```text
users.User
  -> operations.Employee
  -> operations.EmployeeSkill
  -> operations.WorkSchedule / WorkScheduleDay
  -> operations.EmployeeLeave / EmployeeAvailabilityOverride

operations.Task
  -> operations.TaskRequirement
  -> operations.Assignment
  -> operations.AssignmentChangeLog
```
