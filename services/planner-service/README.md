# planner-service

FastAPI сервис планирования для MVP.

## Поток

`PlanRequest` -> eligibility -> scoring -> CP-SAT -> proposals + diagnostics

Текущий MVP хранит planner artifacts in-memory:
- plan run summary
- input snapshot hash + JSON model
- assignment proposals
- unassigned task diagnostics
- solver statistics

Нормализованные `candidate_eligibility`, `candidate_scores`, `constraint_violations` и `replanning_events`
остаются целевой схемой из `docs/dbdiagrams/planner_service.md`, но не внедряются до необходимости.

## API

- `GET /health`
- `POST /api/v1/plan-runs`
- `GET /api/v1/plan-runs/{plan_run_id}`

## Запуск

```bash
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
