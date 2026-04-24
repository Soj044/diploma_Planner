# Planner-Service MVP Backlog

## Goal
Sequence planner-service work in small steps without turning it into a second source of truth for business data.

## Ground Rules
- `core-service` owns employees, schedules, leaves, tasks, and approved assignments.
- `planner-service` owns only planning artifacts and derived diagnostics.
- Shared snapshot and response DTOs live in `packages/contracts`.
- Keep the first iterations synchronous and easy to test.
- Keep the current embedded-snapshot contract only as a bootstrap/testing seam until the real service boundary is added.
- Treat `docs/dbdiagrams/planner_service.md` as a target artifact model, not an all-at-once implementation mandate.

## Phase 1: Plan Run Boundary
- Add an explicit `plan run` command contract with planning period and scope filters.
- Define planner-side `PlanRun` lifecycle states: `created`, `running`, `completed`, `failed`.
- Define the snapshot pull contract from `planner-service` to `core-service`.
- Keep routes thin and move orchestration into a dedicated application service.

## Phase 2: Pipeline Split
- Split planning into separate modules for snapshot loading, eligibility, scoring, optimization, diagnostics, and response assembly.
- Introduce repository interfaces for plan artifacts instead of coupling routes to in-memory storage.
- Keep each stage individually unit-testable with deterministic inputs.

## Phase 3: Artifact Persistence
- Persist the first MVP artifact slice: `PlanRun`, `PlanInputSnapshot`, `AssignmentProposal`, `UnassignedTask`, and `SolverStatistics`.
- Keep normalized `CandidateEligibility`, `CandidateScore`, and `ConstraintViolation` deferred until diagnostics need queryable history.
- Support retrieving a full plan run with summary, proposals, diagnostics, and solver metadata.
- Preserve enough snapshot metadata to explain why a proposal was produced.

## Phase 4: Approval Handoff
- Stabilize proposal DTOs for manager review in `core-service`.
- Define the handoff boundary where approved proposals become `Assignment` records in `core-service`.
- Keep planner outputs immutable after run completion; approvals remain outside planner ownership.

## Phase 5: Hardening
- Add unit tests for eligibility, scoring, diagnostics, and optimization constraints.
- Add integration tests for create-run, snapshot loading, planning, and retrieval.
- Add contracts compatibility checks between `core-service`, `planner-service`, and `packages/contracts`.

## Explicitly Out of Scope for MVP
- RAG or LLM-based planning logic.
- Advanced fairness tuning, preferences, or multi-objective optimization profiles.
- Event-driven orchestration unless synchronous runs become a clear bottleneck.
- `replanning_events`, `llm_score`, approval mirror statuses, and a real worker queue before approval flow exists.
