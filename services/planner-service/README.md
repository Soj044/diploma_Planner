# planner-service

FastAPI сервис планирования для MVP.

## Поток

`CreatePlanRunRequest` -> fetch snapshot from `core-service` -> eligibility -> scoring -> CP-SAT -> proposals + diagnostics

Текущий MVP хранит planner artifacts в SQLite-backed persistence:
- plan run summary
- input snapshot hash + JSON model
- assignment proposals
- unassigned task diagnostics
- solver statistics

`eligibility` и `scores` пока сохраняются как JSON columns на `plan_runs`, а не как отдельные нормализованные таблицы.

Нормализованные `candidate_eligibility`, `candidate_scores`, `constraint_violations` и `replanning_events`
остаются целевой схемой из `docs/dbdiagrams/planner_service.md`, но не внедряются до необходимости.

## API

- `GET /health`
- `POST /api/v1/plan-runs` with `CreatePlanRunRequest`
- `GET /api/v1/plan-runs/{plan_run_id}`

## Review and approval handoff

- Manager reviews persisted proposals via `GET /api/v1/plan-runs/{plan_run_id}`.
- Final approval is not stored in planner-service.
- `core-service` receives `task`, `employee`, `source_plan_run_id`, then re-reads the
  persisted plan run from planner-service before creating the final `Assignment`.
- Planner proposals stay immutable artifacts after run completion.

## Конфигурация

- `CORE_SERVICE_URL` — base URL для `core-service`
- `INTERNAL_SERVICE_TOKEN` — shared token для вызова `/api/v1/planning-snapshot/`
- `PLANNER_DB_PATH` — путь к SQLite-файлу planner artifacts

## Запуск

```bash
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
