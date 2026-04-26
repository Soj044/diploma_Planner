# Architecture Decisions

## ADR-001: MVP Monorepo Bootstrap

- Date: 2026-03-21
- Status: accepted

### Context
Проект стартует с нуля для дипломной MVP-версии. Требуется минимальная, чистая структура без AI-усложнений.

### Decision
- Использовать монорепо с тремя верхнеуровневыми зонами:
  - `services/core-service`
  - `services/planner-service`
  - `packages/contracts`
- Реализовывать последовательно:
  1. `core-service`
  2. `planner-service`
  3. AI-слой только после стабилизации MVP.
- Использовать OR-Tools CP-SAT как основной оптимизационный механизм planner-service.

### Consequences
- Плюсы: проще контроль контрактов, меньше дублирования, предсказуемый MVP scope.
- Минусы: на старте ниже скорость параллельной разработки, чем при full multi-agent split.

## ADR-002: Runtime and Dependency Management for MVP

- Date: 2026-03-21
- Status: accepted

### Context
Проект должен запускаться без локальной ручной установки сервисов на хост-машину.

### Decision
- Использовать Poetry как менеджер зависимостей в каждом backend-сервисе.
- Использовать Docker Compose для локального MVP runtime.
- Использовать PostgreSQL как основную БД для `core-service`.
- Хранить planner артефакты в памяти на первом MVP шаге (без отдельной БД planner).

### Consequences
- Плюсы: предсказуемый запуск, повторяемое окружение, готовность к CI.
- Минусы: planner persistence нужно будет расширить в следующих итерациях.

## ADR-003: Core-Service MVP Schema Alignment

- Date: 2026-04-23
- Status: accepted

### Context
`docs/dbdiagrams/core_service.md` defines the target MVP business schema. The bootstrap implementation used one simplified `operations` app and Django's built-in user model.

### Decision
- Add a dedicated `users` app with a custom Django user model before the schema grows.
- Keep business entities in the `operations` app for now to avoid premature app fragmentation.
- Align model fields, choices, timestamps, constraints, and indexes with the core DB diagram.
- Replace the bootstrap migration with clean initial migrations because there is no production data.

### Consequences
- Плюсы: schema ближе к дипломной модели, кастомный пользователь зафиксирован рано, CRUD остается простым.
- Минусы: initial migration reset допустим только пока проект находится в bootstrap-стадии.

## ADR-004: Planner Snapshot Pull Boundary

- Date: 2026-04-24
- Status: accepted

### Context
Planner-service больше не должен принимать business truth как внешний embedded payload в production-like flow. Нужна простая и проверяемая граница между `core-service` и `planner-service`, не создающая второй источник истины.

### Decision
- Публичная команда planner-service: `CreatePlanRunRequest`.
- Planner-service сам запрашивает `PlanningSnapshot` у `core-service` через `POST /api/v1/planning-snapshot/`.
- `core-service` отдает snapshot для аутентифицированного пользователя или для внутреннего service-to-service вызова с shared header token `X-Internal-Service-Token`.
- Полный `PlanningSnapshot` остается допустимым только для внутренних planning tests и низкоуровневых pipeline checks.

### Consequences
- Плюсы: одна стабильная service boundary, planner не дублирует бизнес-логику core, интеграцию проще тестировать.
- Минусы: появляется простая внутренняя secret-конфигурация между сервисами, а planner create flow теперь зависит от доступности `core-service`.

## ADR-005: Minimal Planner Artifact Persistence

- Date: 2026-04-24
- Status: accepted

### Context
После стабилизации snapshot boundary planner-service всё ещё хранил результаты planning run только в памяти процесса. Это не позволяло читать run после рестарта сервиса и мешало двигаться к approval flow, завязанному на реальные planner artifacts.

### Decision
- Перевести runtime planner repository с `in-memory` на локальный SQLite-backed storage.
- Сохранять минимальный Stage 6 slice: `plan_runs`, `plan_input_snapshots`, `assignment_proposals`, `unassigned_tasks`, `solver_statistics`.
- Держать `eligibility` и `scores` в JSON columns на `plan_runs`, а не раскладывать их сразу по отдельным таблицам.
- Считать PostgreSQL из `docs/dbdiagrams/planner_service.md` целевой схемой следующего уровня, а SQLite — MVP runtime persistence без лишней инфраструктуры.

### Consequences
- Плюсы: planner runs переживают рестарт процесса, retrieval API читает реальные артефакты, код остаётся простым и без ORM.
- Минусы: SQLite подходит только для MVP single-instance режима; при росте нагрузки и multi-instance planner понадобится переход к полноценной planner DB.

## ADR-006: Approval Handoff Reads Persisted Planner Artifacts

- Date: 2026-04-25
- Status: accepted

### Context
После появления persisted planner runs менеджеру нужен простой и проверяемый способ утвердить одно из предложений, не превращая `planner-service` в владельца финальных назначений и не дублируя бизнес-истину между сервисами.

### Decision
- Менеджер читает proposals из `planner-service` через `GET /api/v1/plan-runs/{plan_run_id}`.
- Менеджер отправляет в `core-service` только минимальный handoff payload: `task`, `employee`, `source_plan_run_id`, optional `notes`.
- `core-service` сам перечитывает persisted plan run из `planner-service`, ищет matching proposal, валидирует `run.status == completed`, `proposal.status == proposed`, `proposal.is_selected == true`, и только после этого создаёт final `Assignment` и `AssignmentChangeLog`.
- Planner proposals остаются immutable artifacts после завершения run; approval не меняет planner в MVP.
- Handoff должен быть idempotent для одного и того же `task + employee + source_plan_run_id`.

### Consequences
- Плюсы: финальная бизнес-истина остаётся только в `core-service`, approval payload минимален, а retry/manager UI можно делать безопасно.
- Минусы: approval flow теперь зависит от доступности `planner-service`, а полная защита от конкурентных approvals остаётся на стороне транзакций и core-service проверок.
