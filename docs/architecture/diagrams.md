# Architecture Diagrams

## High-Level Service Flow (MVP)

```text
manager -> core-service: create/update employees, skills, schedules, tasks
manager -> planner-service: POST /api/v1/plan-runs (CreatePlanRunRequest)
planner-service -> core-service: POST /api/v1/planning-snapshot/ + X-Internal-Service-Token
planner-service (CP-SAT): eligibility -> scoring -> optimization
planner-service -> planner artifact store: save run + snapshot + proposals + diagnostics
planner-service -> manager: assignment proposals + diagnostics
manager -> planner-service: GET /api/v1/plan-runs/{id}
manager -> core-service: approve proposals
core-service: store final approved assignments
```

## Approval Handoff

```text
manager -> planner-service: review proposal
manager -> core-service: POST /api/v1/assignments/approve-proposal/
core-service -> core database: create approved Assignment + AssignmentChangeLog
planner-service: keeps proposal as planning artifact only
```

## Runtime Diagram (Docker)

```text
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
