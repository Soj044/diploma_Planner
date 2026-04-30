# Docs

This directory contains architecture, domain, planner flow, testing, engineering rules, and frontend task context.

## Current MVP Focus
- keep `core-service` as the business source of truth for users, employees, schedules, leaves, tasks, and final assignments;
- keep `planner-service` responsible for persisted plan runs, proposals, diagnostics, and solver stats;
- keep `frontend-app` as a thin browser client over real backend contracts instead of a second source of truth;
- support two final-assignment paths in `core-service`: persisted planner approval and explicit manager/admin manual assignment;
- keep architecture minimal, explicit, and testable while frontend stages catch up with the latest backend RBAC and lifecycle rules.

## Frontend Task Context

- `docs/project/frontend-vue-chat-prompt.md` is the current backend-truth snapshot for Vue work.
- Use it before frontend tasks that touch auth bootstrap, employee self-service, leave review, or dual assignment flows.
