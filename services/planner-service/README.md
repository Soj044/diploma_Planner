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
- `POST /api/v1/plan-runs` with `CreatePlanRunRequest` (requires Bearer token, `admin|manager`)
- `GET /api/v1/plan-runs/{plan_run_id}` (requires Bearer token, `admin|manager`, or trusted internal reread token from `core-service`)
- `GET /api/v1/internal/ai/service-boundary` (requires `X-Internal-Service-Token`)
- `GET /api/v1/internal/ai/index-feed` (requires `X-Internal-Service-Token`)
- `GET /api/v1/internal/ai/plan-runs/{plan_run_id}/proposal-context` (requires `X-Internal-Service-Token`)
- `GET /api/v1/internal/ai/plan-runs/{plan_run_id}/unassigned-context` (requires `X-Internal-Service-Token`)

## Review and approval handoff

- Manager reviews persisted proposals via `GET /api/v1/plan-runs/{plan_run_id}`.
- Final approval is not stored in planner-service.
- `core-service` receives `task`, `employee`, `source_plan_run_id`, then re-reads the
  persisted plan run from planner-service with `X-Internal-Service-Token` before creating the final `Assignment`.
- Planner proposals stay immutable artifacts after run completion.

## Hardening status

- Shared contracts validate planning period boundaries and proposal assignment dates.
- Planner tests cover hard eligibility failures, weighted scoring, overlap conflicts,
  persisted artifact roundtrip, and approval-critical response fields.

## Конфигурация

- `CORE_SERVICE_URL` — base URL для `core-service`
- `INTERNAL_SERVICE_TOKEN` — shared token для вызова `/api/v1/planning-snapshot/` и `/api/v1/auth/introspect`
- `PLANNER_DB_PATH` — путь к SQLite-файлу planner artifacts

## Internal AI helper boundary

`GET /api/v1/internal/ai/service-boundary` returns a compact description of
planner ownership over proposals, diagnostics, and persisted planning artifacts.
It is available only to trusted backend callers that send the shared
`X-Internal-Service-Token`.

`GET /api/v1/internal/ai/index-feed` returns flattened `unassigned_case`
records for completed persisted plan runs only. The v1 feed is append-only and
uses persisted snapshot, diagnostics, eligibility, scores, and solver summary
to build retrieval items for `ai-layer`.

`GET /api/v1/internal/ai/plan-runs/{plan_run_id}/proposal-context` returns the
persisted proposal slice for one `task_id + employee_id` pair, including the
task snapshot, target proposal, sibling proposals, eligibility list, score map,
and solver summary.

`GET /api/v1/internal/ai/plan-runs/{plan_run_id}/unassigned-context` returns
the persisted diagnostic slice for one task, including the task snapshot,
matching unassigned diagnostic, eligibility list, score map, and solver summary.

## Запуск

```bash
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
