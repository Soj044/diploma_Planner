# Docs

This directory contains architecture, domain, planner flow, testing, and engineering rules.

## Current MVP Focus
- bootstrap monorepo with `core-service`, `planner-service`, and shared `contracts`;
- add a thin `frontend-app` shell without changing backend ownership boundaries;
- implement planning flow without AI/RAG;
- run backend services via Docker Compose;
- keep architecture minimal, explicit, and testable.
