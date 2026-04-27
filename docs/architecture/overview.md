# Architecture Overview

## Services
- `core-service` (Django + DRF): source of truth for business entities and final approved assignments.
- `planner-service` (FastAPI + OR-Tools / CP-SAT): planning runs, snapshots, eligibility, scoring, proposals, diagnostics.
- `frontend-app` (Vue 3 + Vite): thin manager-facing UI over existing backend contracts; not a source of business truth.
- `ai-layer` (future): optional support layer after MVP; not implemented in this stage.

## Core-Service Structure
- `users`: custom Django user model with MVP roles.
- `operations`: business entities for departments, employees, skills, schedules, leaves, tasks, and assignments.
- This split keeps authentication separate while avoiding premature domain app fragmentation.

## Monorepo Layout (MVP)
- `services/core-service`
- `services/planner-service`
- `frontend-app`
- `services/ai-layer`
- `packages/contracts`
- `docs/`

## Runtime Topology
- `docker-compose` orchestrates:
  - `postgres` as primary database for `core-service`
  - `core-service` API on port `8000`
  - `planner-service` API on port `8001`
- `frontend-app` currently runs as a separate Vite dev server on port `5173`
- local frontend development uses Vite proxies `/core-api` -> `core-service` and `/planner-api` -> `planner-service`

## Main Principle
- `core-service` is the source of truth for employees, schedules, leaves, tasks, and approved assignments.
- `planner-service` stores planning artifacts and never becomes a second source of truth for business entities.
- `frontend-app` keeps only transient UI state and submits all business changes through backend APIs.
- `planner-service` uses logical external IDs for core entities; it must not create database foreign keys into `core-service`.
- Manager review happens against persisted planner runs, but manager approval is executed by `core-service`, which re-reads the selected planner proposal before writing the final assignment.
