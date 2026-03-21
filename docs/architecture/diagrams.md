# Architecture Diagrams

## High-Level Service Flow (MVP)

```text
manager -> core-service: create/update employees, skills, schedules, tasks
planner-service -> core-service: read snapshot inputs for planning run
planner-service (CP-SAT): eligibility -> scoring -> optimization
planner-service -> manager: assignment proposals + diagnostics
manager -> core-service: approve proposals
core-service: store final approved assignments
```

## Runtime Diagram (Docker)

```text
+---------------------+      +-----------------------+
|   core-service      |<---->|       postgres        |
|   django + drf      |      |      postgres:16      |
+----------+----------+      +-----------------------+
           |
           v
+---------------------+
|   planner-service   |
|  fastapi + or-tools |
+---------------------+
```

## Data Ownership

```text
core-service:
  User, Department, Employee, Skill, EmployeeSkill,
  WorkSchedule, WorkScheduleDay, EmployeeLeave,
  EmployeeAvailabilityOverride, Task, TaskRequirement,
  Assignment, AssignmentChangeLog

planner-service:
  PlanRun, PlanInputSnapshot, CandidateEligibility,
  CandidateScore, AssignmentProposal, UnassignedTask,
  ConstraintViolation, SolverStatistics
```
