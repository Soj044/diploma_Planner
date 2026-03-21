# Project Agent Instructions

## Mission
Implement and maintain the diploma project with predictable quality, clear architecture, and low knowledge loss.

Project goal:
build an automated operational planning and task assignment system for a small enterprise unit.

Main system parts:
1. core-service — Django + DRF
2. planner-service — FastAPI + OR-Tools / CP-SAT
3. ai-layer — optional RAG/LLM support, added after MVP

The system should:
- store employees, skills, schedules, leaves, tasks, and approved assignments
- generate assignment proposals for a selected planning period
- allow manager review and approval
- remain explainable and testable

## Mandatory Read Order
1. `README.md`
2. `docs/README.md`
3. `docs/project/brief.md`
4. `docs/architecture/overview.md`
5. `docs/domain/domain-model.md`
6. `docs/planner/planning-flow.md`
7. `docs/architecture/diagrams.md`
8. `docs/engineering/best-practices.md`
9. `docs/testing/strategy.md`
10. `.ai/team/workflow.md`

## Non-Negotiable Rules
- Keep changes minimal and reversible.
- Update impacted docs in the same task.
- Record architecture-impacting decisions in `docs/architecture/decisions.md`.
- Update `docs/architecture/diagrams.md` when architecture, data flow, or critical workflow changes.
- Do not introduce major architecture changes without documenting the reason and tradeoffs.
- Add or update verification steps in `docs/testing/strategy.md` when behavior changes.
- Apply best practices from `docs/engineering/best-practices.md` in every task.
- Do not add AI-style comments to code; keep only useful comments for non-obvious logic.
- Write useful docstrings for public modules, classes, and functions.
- Use typed Python where reasonable.
- Prefer small, testable functions and explicit service boundaries.
- Do not duplicate business truth between services.
- core-service is the source of truth for business entities.
- planner-service stores planning runs, snapshots, eligibility results, scores, proposals, and diagnostics.
- Final approved assignments must be stored by core-service.
- Do not start with RAG implementation unless the task explicitly asks for it.
- Do not replace planning solver logic with LLM logic.
- Prefer correctness and clarity over premature abstractions.

## Architecture Constraints
### core-service
Use Django + DRF for:
- users and employee profiles
- departments
- skills and employee skills
- work schedules and schedule days
- employee leaves and availability overrides
- tasks and task requirements
- approved assignments
- audit-friendly CRUD and admin support

### planner-service
Use FastAPI for:
- planning run creation
- input snapshot creation
- candidate eligibility evaluation
- candidate scoring
- assignment proposal generation
- unassigned task diagnostics
- solver statistics

Use OR-Tools / CP-SAT for the optimization layer.

### ai-layer
Treat AI/RAG as a support layer, not as the primary planner.
Use it later for:
- parsing task descriptions
- retrieving similar historical tasks
- supporting explanations
- optionally contributing auxiliary llm_score signals

## Delivery Order
Follow this implementation order unless the task explicitly overrides it:
1. repository structure
2. core-service scaffold
3. planner-service scaffold
4. shared contracts between services
5. core domain models and migrations
6. planning flow without AI
7. approval flow
8. tests and docs
9. RAG/LLM integration after MVP

## Task Output Contract
Always provide:
- Scope completed
- Files changed
- Verification commands run
- Residual risks / follow-ups
- Docs updated
- Diagram update status
- Explicit assumptions, when context is incomplete

## If Context Is Missing
- State assumptions explicitly.
- Prefer the simplest architecture that matches project goals.
- Do not invent major business rules silently.
- Add TODO markers only with owner and trigger condition.

## Current MVP Domain
Core-service entities expected:
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

Planner-service entities expected:
- PlanRun
- PlanInputSnapshot
- CandidateEligibility
- CandidateScore
- AssignmentProposal
- UnassignedTask
- ConstraintViolation
- SolverStatistics

## What To Avoid
- Do not build everything at once.
- Do not start with frontend-first implementation.
- Do not add external integrations before the core planning flow works.
- Do not introduce a second source of truth for employees or tasks.
- Do not overengineer permissions, notifications, or AI infrastructure before MVP is stable.