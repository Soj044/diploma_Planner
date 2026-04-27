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

## ADR-007: Frontend MVP Shell Uses Vue 3 + Vite as a Thin Client

- Date: 2026-04-26
- Status: accepted

### Context
Backend MVP уже стабилизирован достаточно, чтобы поверх него появился первый browser-facing слой. Нужен минимальный фронтенд, который не станет вторым источником истины и не будет перетаскивать planner logic в браузер.

### Decision
- Добавить `frontend-app` в корень монорепо как отдельный Vue 3 + Vite + TypeScript проект.
- Использовать обязательный router и отдельные API-модули для `core-service` и `planner-service`.
- Не вводить Pinia и общий client-side business state до тех пор, пока реальная shared state между экранами не станет необходимой.
- В локальной разработке использовать Vite proxy для `/core-api` и `/planner-api`, чтобы не блокировать frontend shell на CORS-настройках backend.
- До появления полноценного frontend auth flow считать допустимым только локальное MVP-допущение: `core-service` может вызываться через явно заданные Basic credentials в frontend env.

### Consequences
- Плюсы: появляется минимальная, понятная точка входа для manager UI; backend contracts переиспользуются без редизайна; dev-среда проста и обратима.
- Минусы: auth flow пока остаётся временным и непригодным для production; frontend shell пока покрывает только каркас и навигацию, без полноценных CRUD/user flows.

## ADR-008: Token-Based API Auth with Core-Service as Auth Authority

- Date: 2026-04-27
- Status: accepted

### Context
Frontend-app уже использует отдельный browser runtime и обращается сразу к двум backend-сервисам (`core-service` и `planner-service`). Session-only auth неудобен для такого SPA-потока и не дает стабильного механизма role-check в `planner-service`.

### Decision
- Использовать JWT-based auth для API в `core-service`:
  - short-lived access token в JSON ответе;
  - refresh token в HttpOnly cookie;
  - refresh token rotation + blacklist.
- Сохранить Django session auth как вспомогательный канал для `/admin/`.
- Добавить auth endpoints:
  - `POST /api/v1/auth/signup`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me`
  - `POST /api/v1/auth/introspect` для внутренней проверки access tokens.
- `core-service` считается единственным auth authority для остальных сервисов.

### Consequences
- Плюсы: стабильный API auth flow для frontend, единый источник role/user контекста, готовая база для planner role-gate через introspection.
- Минусы: появляется дополнительная ответственность у `core-service` за token lifecycle и cookie-политику; требуется согласованная настройка internal token и cookie параметров в окружениях.
