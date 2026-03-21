# Architecture Overview

## Services
- `core-service` (Django + DRF): source of truth for business entities and final approved assignments.
- `planner-service` (FastAPI + OR-Tools / CP-SAT): planning runs, snapshots, eligibility, scoring, proposals, diagnostics.
- `ai-layer` (future): optional support layer after MVP; not implemented in this stage.

## Monorepo Layout (MVP)
- `services/core-service`
- `services/planner-service`
- `services/ai-layer`
- `packages/contracts`
- `docs/`

## Runtime Topology
- `docker-compose` orchestrates:
  - `postgres` as primary database for `core-service`
  - `core-service` API on port `8000`
  - `planner-service` API on port `8001`

## Main Principle
- `core-service` is the source of truth for employees, schedules, leaves, tasks, and approved assignments.
- `planner-service` stores planning artifacts and never becomes a second source of truth for business entities.
