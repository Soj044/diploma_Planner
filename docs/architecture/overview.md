# Architecture Overview

## Services
- `core-service` (Django + DRF): source of truth for business entities and final approved assignments.
- `planner-service` (FastAPI + OR-Tools / CP-SAT): planning runs, snapshots, eligibility, scoring, proposals, diagnostics.
- `ai-layer` (future): optional support layer after MVP; not implemented in this stage.

## Monorepo Layout (MVP)
- `services/core-service`
- `services/planner-service`
- `packages/contracts`
- `docs/`

## Main Principle
- `core-service` is the source of truth for employees, schedules, leaves, tasks, and approved assignments.
- `planner-service` stores only planning artifacts and never becomes a second source of truth for business entities.
