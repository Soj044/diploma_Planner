# Planner-Service MVP Backlog

## Goal
Sequence planner-service work in small steps without turning it into a second source of truth for business data.

## Ground Rules
- `core-service` owns employees, schedules, leaves, tasks, and approved assignments.
- `planner-service` owns only planning artifacts and derived diagnostics.
- Shared snapshot and response DTOs live in `packages/contracts`.
- Keep the first iterations synchronous and easy to test.
- Keep embedded `PlanningSnapshot` usage only as a bootstrap/testing seam; the public planner boundary is `CreatePlanRunRequest`.
- Treat `docs/dbdiagrams/planner_service.md` as a target artifact model, not an all-at-once implementation mandate.

## Phase 1: Plan Run Boundary
- Add an explicit `plan run` command contract with planning period and scope filters.
- Define planner-side `PlanRun` lifecycle states: `created`, `running`, `completed`, `failed`.
- Define the snapshot pull contract from `planner-service` to `core-service`.
- Keep routes thin and move orchestration into a dedicated application service.
- Current MVP cut: `POST /api/v1/plan-runs` accepts `CreatePlanRunRequest`, then planner pulls `/api/v1/planning-snapshot/` from core-service.

## Phase 2: Pipeline Split
- Split planning into separate modules for snapshot loading, eligibility, scoring, optimization, diagnostics, and response assembly.
- Introduce repository interfaces for plan artifacts instead of coupling routes to in-memory storage.
- Keep each stage individually unit-testable with deterministic inputs.

## Phase 3: Artifact Persistence
- Persist the first MVP artifact slice: `PlanRun`, `PlanInputSnapshot`, `AssignmentProposal`, `UnassignedTask`, and `SolverStatistics`.
- Keep normalized `CandidateEligibility`, `CandidateScore`, and `ConstraintViolation` deferred until diagnostics need queryable history.
- Support retrieving a full plan run with summary, proposals, diagnostics, and solver metadata.
- Preserve enough snapshot metadata to explain why a proposal was produced.
- Current MVP cut: use a SQLite-backed repository that mirrors these planner tables and keeps `eligibility` / `scores` in JSON columns on `plan_runs` until normalization is justified.

## Phase 4: Approval Handoff (completed)
- Stabilize proposal DTOs for manager review through `GET /api/v1/plan-runs/{plan_run_id}`.
- Support the handoff boundary where `core-service` reads persisted planner artifacts before creating final `Assignment` records.
- Keep planner outputs immutable after run completion; approvals remain outside planner ownership.

## Phase 5: Hardening (completed)
- Add unit tests for eligibility, scoring, diagnostics, and optimization constraints.
- Add integration tests for create-run, snapshot loading, planning, and retrieval.
- Add contracts compatibility checks between `core-service`, `planner-service`, and `packages/contracts`.
- Final MVP cut: planner tests now cover partial/insufficient availability, weighted scoring with cap, overlap conflicts, SQLite artifact roundtrip, and shared contracts validation for planning periods and proposal dates.

## Phase 6: Planner Auth Gate (completed)
- Protect `POST /api/v1/plan-runs` and `GET /api/v1/plan-runs/{id}` with Bearer token auth.
- Validate incoming access token through `core-service /api/v1/auth/introspect`.
- Allow planner runs only for `admin` and `manager`, deny `employee`.
- Return controlled auth dependency errors (`401`, `403`, `503`) when token is missing/invalid or introspection is unavailable.

## Explicitly Out of Scope for MVP
- RAG or LLM-based planning logic.
- Advanced fairness tuning, preferences, or multi-objective optimization profiles.
- Event-driven orchestration unless synchronous runs become a clear bottleneck.
- `replanning_events`, `llm_score`, approval mirror statuses, and a real worker queue before approval flow exists.
