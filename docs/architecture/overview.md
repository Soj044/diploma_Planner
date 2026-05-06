# Architecture Overview

## Services
- `core-service` (Django + DRF): source of truth for business entities and final approved assignments.
- `planner-service` (FastAPI + OR-Tools / CP-SAT): planning runs, snapshots, eligibility, scoring, proposals, diagnostics.
- `frontend-app` (Vue 3 + Vite): thin manager/employee UI over existing backend contracts; not a source of business truth.
- `ai-layer` (FastAPI): support layer for future AI features; current scope includes runtime bootstrap, authenticated capability checks, and internal-service boundary wiring, but it is not a source of business truth.

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
  - `postgres` with `pgvector` as primary database for `core-service` and derived `ai-layer` storage
  - `core-service` API on port `8000`
  - `planner-service` API on port `8001`
  - `ai-layer` API on port `8002`
  - `ollama` local model runtime on port `11434`
  - `frontend-app` as a Vite dev container on port `5173`
- `frontend-app` can still run standalone on the host when faster UI iteration is needed
- frontend development uses Vite proxies `/api` -> `core-service`, `/planner-api` -> `planner-service`, and reserves `/ai-api` -> `ai-layer`
- `ai-layer` bootstraps `CREATE EXTENSION IF NOT EXISTS vector` and an isolated `ai_layer` schema inside the shared PostgreSQL instance
- frontend-facing `ai-layer` routes use the same Bearer-to-introspection pattern as `planner-service`: browser Bearer token -> `core-service /api/v1/auth/introspect` with `X-Internal-Service-Token`
- `core-service` and `planner-service` both expose internal AI helper endpoints only through `X-Internal-Service-Token`

## Main Principle
- `core-service` is the source of truth for employees, schedules, leaves, tasks, and approved assignments.
- `planner-service` is the source of truth for planning proposals, diagnostics, and related persisted artifacts.
- `frontend-app` keeps only transient UI state and submits all business changes through backend APIs.
- `ai-layer` may keep only derived retrieval/index data, explanations, and sync metadata in its own schema and must not mirror or own business truth from `core-service` or planning truth from `planner-service`.
- `planner-service` uses logical external IDs for core entities; it must not create database foreign keys into `core-service`.
- Manager review happens against persisted planner runs, but manager approval is executed by `core-service`, which re-reads the selected planner proposal before writing the final assignment.
