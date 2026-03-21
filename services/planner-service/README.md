# planner-service

FastAPI сервис планирования для MVP.

## Поток

`PlanRequest` -> eligibility -> scoring -> CP-SAT -> proposals + diagnostics

## API

- `GET /health`
- `POST /api/v1/plan-runs`
- `GET /api/v1/plan-runs/{plan_run_id}`
