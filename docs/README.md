# Docs

This directory contains architecture, domain, planner flow, testing, engineering rules, and frontend task context.

## Current MVP Focus
- stabilize the monorepo around `core-service`, `planner-service`, `frontend-app`, and shared `contracts`;
- keep `core-service` as the business source of truth for users, employees, schedules, leaves, tasks, and final assignments;
- keep `planner-service` as the owner of persisted planning artifacts, proposals, diagnostics, and solver stats only;
- keep `frontend-app` as a thin browser client over real backend contracts instead of a second source of truth;
- support the current manager/admin flow: reference data -> `/tasks/new` -> single-task planner suggestion or manual assignment -> read-only assignments, while `/planning` remains an advanced compatibility route;
- support the employee flow: signup, assignment-first tasks, read-only schedules, requested-only leaves, departments directory, and auth-backed profile;
- support two final-assignment paths in `core-service`: persisted planner approval and explicit manager/admin manual assignment;
- run the full local dev runtime via `docker compose up --build`;
- keep user-facing AI/RAG flows out of scope until the non-AI MVP remains stable, explicit, and testable;
- allow only the bootstrap AI runtime/storage foundation for `ai-layer`, `ollama`, and shared `pgvector`.

## Frontend Task Context

- `docs/project/frontend-vue-chat-prompt.md` is the current backend-truth snapshot for Vue work.
- Use it before frontend tasks that touch auth bootstrap, employee self-service, leave review, or dual assignment flows.
