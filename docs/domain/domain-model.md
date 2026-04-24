# Domain Model

## Core entities
- User
- Department
- Employee
- Skill
- EmployeeSkill
- WorkSchedule
- WorkScheduleDay
- EmployeeLeave
- EmployeeAvailabilityOverride
- Task
- TaskRequirement
- Assignment
- AssignmentChangeLog

## Core implementation note
`User` lives in the `users` app. The remaining MVP business entities live in the `operations` app until the domain needs a split.

## Planner entities
- PlanRun
- PlanInputSnapshot
- CandidateEligibility
- CandidateScore
- AssignmentProposal
- UnassignedTask
- ConstraintViolation
- SolverStatistics

## Planner implementation note
Planner entities represent artifacts copied or derived from a run. They reference core entities by logical external IDs and do not own employee, task, or final assignment truth.
