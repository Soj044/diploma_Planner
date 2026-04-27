# Architecture Diagrams

## Editable Draw.io Files

- [class-diagram.drawio](/home/oleg/PycharmProjects/Workestrator/docs/architecture/class-diagram.drawio)
- [task-creation-and-final-assignment-flow.drawio](/home/oleg/PycharmProjects/Workestrator/docs/architecture/task-creation-and-final-assignment-flow.drawio)
- [employee-selection-algorithm.drawio](/home/oleg/PycharmProjects/Workestrator/docs/architecture/employee-selection-algorithm.drawio)

## High-Level Service Flow (MVP)

```text
manager -> frontend-app: navigate CRUD, planning, review, approval screens
frontend-app -> core-service: create/update employees, skills, schedules, tasks
frontend-app -> planner-service: POST /api/v1/plan-runs (CreatePlanRunRequest)
planner-service -> core-service: POST /api/v1/planning-snapshot/ + X-Internal-Service-Token
planner-service (CP-SAT): eligibility -> scoring -> optimization
planner-service -> planner artifact store: save run + snapshot + proposals + diagnostics
planner-service -> frontend-app: assignment proposals + diagnostics
frontend-app -> planner-service: GET /api/v1/plan-runs/{id}
frontend-app -> core-service: POST /api/v1/assignments/approve-proposal/
core-service -> planner-service: GET /api/v1/plan-runs/{id}
core-service -> core database: store final approved assignments
```

## Approval Handoff

```text
manager -> planner-service: review proposal
manager -> core-service: POST /api/v1/assignments/approve-proposal/
core-service -> planner-service: GET /api/v1/plan-runs/{id}
core-service: validate run status + proposal pair + idempotency
core-service -> core database: create approved Assignment + AssignmentChangeLog
planner-service: keeps proposal immutable as planning artifact only
```

## Runtime Diagram (Docker)

```text
browser
  |
  v
+---------------------+
|    frontend-app     |
|    vue + vite dev   |
|       :5173         |
+----------+----------+
           | /core-api, /planner-api
           v
+---------------------+      +-----------------------+
|   core-service      |<---->|       postgres        |
|   django + drf      |      |      postgres:16      |
+----------+----------+      +-----------------------+
           ^
           | POST /api/v1/planning-snapshot/
           | X-Internal-Service-Token
           |
           |
+---------------------+      +-----------------------+
|   planner-service   |----->|   planner sqlite db   |
|  fastapi + or-tools |      |   planner.sqlite3     |
+---------------------+      +-----------------------+
```

## Frontend Boundary

```text
frontend-app:
  routes:
    shell, reference-data, tasks, planning, assignments

  client modules:
    services/core-service.ts
    services/planner-service.ts
    services/http.ts

  rules:
    no planner eligibility/scoring logic in browser
    no frontend-owned business truth
    token auth via core-service (access bearer + refresh cookie)
```

## Auth Flow (MVP)

```text
frontend-app -> core-service: POST /api/v1/auth/login
core-service -> frontend-app: access token (JSON) + refresh token (HttpOnly cookie)
frontend-app -> core-service: GET /api/v1/auth/me (Authorization: Bearer <access>)
frontend-app -> core-service: POST /api/v1/auth/refresh (refresh cookie)
core-service -> frontend-app: rotated refresh cookie + new access token
planner-service -> core-service: POST /api/v1/auth/introspect + X-Internal-Service-Token
core-service -> planner-service: user_id + role + is_active + employee_id
```

## RBAC Boundary (Core-Service)

```text
admin:
  full access to users + operations CRUD + approval

manager:
  operational access (tasks/schedules/overrides/approval) with restricted destructive paths

employee:
  read-only tasks + self-scope CRUD (own schedules, own schedule days, own leaves)

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
