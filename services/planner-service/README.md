# planner-service

FastAPI сервис планирования для MVP.

## Поток

`PlanRequest` -> eligibility -> scoring -> CP-SAT -> proposals + diagnostics

## API

- `GET /health`
- `POST /api/v1/plan-runs`
- `GET /api/v1/plan-runs/{plan_run_id}`

## Запуск

```bash
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
