# planner-service

FastAPI сервис планирования для MVP.

## Поток

`CreatePlanRunRequest` -> fetch snapshot from `core-service` -> eligibility -> scoring -> CP-SAT -> proposals + diagnostics

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
- `POST /api/v1/plan-runs` with `CreatePlanRunRequest`
- `GET /api/v1/plan-runs/{plan_run_id}`

## Конфигурация

- `CORE_SERVICE_URL` — base URL для `core-service`
- `INTERNAL_SERVICE_TOKEN` — shared token для вызова `/api/v1/planning-snapshot/`

## Запуск

```bash
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
