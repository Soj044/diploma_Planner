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
- Update note (2026-04-27): the runtime access policy was later narrowed by ADR-010. In the current MVP, `POST /api/v1/planning-snapshot/` is internal-token only and no longer accepts ordinary user-token access.

### Update Note (2026-04-30)
- `planning-snapshot` больше не считается endpoint для обычных authenticated user flows.
- Актуальная MVP boundary: `POST /api/v1/planning-snapshot/` доступен только через `X-Internal-Service-Token`.

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

### Update Note (2026-04-30)
- Stage 1 добавил второй backend-owned путь создания final `Assignment`: `POST /api/v1/assignments/manual/`.
- Planner approval path не удалён и остаётся обязательным для persisted proposal handoff через reread planner artifacts.

### Update Note (2026-05-01)
- Final assignment lifecycle now also synchronizes task lifecycle in `core-service`:
  - planner approval and manual assignment move `Task.status` to `assigned`;
  - assignment rejection reopens the task to `planned`.
- The frontend canonical create-and-assign UX may launch a single-task persisted run from `/tasks/new`, but approval still uses the same persisted handoff boundary and does not create final assignments in the browser.

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
- Update note (2026-04-28/2026-04-29): the bootstrap runtime/auth details in this ADR were later superseded by ADR-012 and ADR-014. The current MVP uses token auth, same-origin `/api/*` plus `/planner-api/*` proxies, and a Docker Compose Vite runtime for `frontend-app`.

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

## ADR-009: Auto-Creation of Employee Profile for Manager and Employee Roles

- Date: 2026-04-27
- Status: accepted

### Context
В MVP пользователи с ролями `manager` и `employee` должны иметь employee profile, иначе self-scope flow и часть planning-boundary логики становятся хрупкими и требуют ручных шагов после создания пользователя.

### Decision
- При signup, user-create и role-change автоматически создавать `Employee` profile для ролей `manager` и `employee`, если профиль отсутствует.
- При смене роли на `admin` существующий `Employee` profile не удалять.
- Использовать безопасные defaults: `full_name` из user данных или email, `position_name = "Pending assignment"`, `employment_type = full_time`, `weekly_capacity_hours = 40`, `timezone = "UTC"`.

### Consequences
- Плюсы: меньше ручных шагов в CRUD и auth flows, стабильный `me` payload и проще подготовка данных для planning.
- Минусы: появляется связанная логика между `users` и `operations`, поэтому изменения role semantics должны проверяться интеграционными тестами.

## ADR-010: Core-Service RBAC with Deny-by-Default and Employee Self-Scope

- Date: 2026-04-27
- Status: accepted

### Context
После добавления token auth по умолчанию любой аутентифицированный пользователь всё ещё имел доступ к большинству CRUD операций. Для MVP нужны явные role boundaries: admin full access, manager operational access, employee self-scope + read-only task visibility.

### Decision
- В `core-service` внедрить role-aware permission classes для каждого resource viewset:
  - `admin`: полный доступ;
  - `manager`: operational CRUD/read доступ согласно MVP матрице;
  - `employee`: только self-scope на графики/leave и read-only доступ к задачам.
- Закрыть `users` API для не-admin ролей.
- Закрыть `planning-snapshot` от обычных user tokens и оставить только `X-Internal-Service-Token`.
- Оставить assignment approval (`/assignments/approve-proposal`) только для `admin` и `manager`.

### Consequences
- Плюсы: предсказуемая модель прав, защита от случайного расширения доступа, готовая база для planner role-gate.
- Минусы: больше permission-кода и тестов; любые изменения бизнес-ролей требуют синхронного обновления permission matrix и API-тестов.

### Update Note (2026-04-30)
- Employee self-scope уточнён:
  - `work-schedules` и `work-schedule-days` теперь read-only для employee;
  - `employee-leaves` остаются self-scope, но employee может менять только requested leaves;
  - `assignments` теперь доступны employee в read-only self-scope;
  - manager/admin leave review идёт через status-only action, а не generic leave PATCH.

## ADR-011: Planner-Service Access via Core Introspection

- Date: 2026-04-27
- Status: accepted

### Context
После внедрения token auth и RBAC в `core-service` planner endpoints оставались открытыми, что позволяло запускать planning без user-role контроля. Нужен простой, единый способ авторизации planner запросов без дублирования auth logic в `planner-service`.

### Decision
- Защитить `planner-service` routes `POST /api/v1/plan-runs` и `GET /api/v1/plan-runs/{id}` через Bearer token dependency.
- Валидировать access token в `planner-service` через `core-service /api/v1/auth/introspect` с `X-Internal-Service-Token`.
- Разрешить planner routes только ролям `admin` и `manager`.
- Для ошибок auth dependency использовать контролируемые ответы:
  - `401` для отсутствующего/некорректного Bearer token;
  - `403` для запрещенной роли или неактивного пользователя;
  - `503` при недоступности introspection.

### Consequences
- Плюсы: единый auth authority в `core-service`, planner не хранит user sessions или refresh tokens, политика доступа согласована с core RBAC.
- Минусы: planner create/get теперь зависят от доступности `core-service` introspection endpoint и internal token конфигурации.

## ADR-013: Core Approval Reread Uses Internal Planner Read Access

- Date: 2026-04-29
- Status: accepted

### Context
После того как `planner-service` стал требовать Bearer token на `GET /api/v1/plan-runs/{id}`, approval handoff в `core-service` начал ломаться: manager approval приходит в `core-service`, но сам reread persisted planner artifact выполняется уже не от лица браузера. Передавать browser access token дальше внутрь `core-service` не хотелось, потому что final approval должен оставаться backend-owned handoff, а не browser token relay.

### Decision
- Сохранить manager/admin Bearer доступ для browser review на `GET /api/v1/plan-runs/{id}`.
- Дополнительно разрешить trusted internal reread того же persisted route по `X-Internal-Service-Token` только для backend handoff из `core-service`.
- Обновить `core-service` planner client так, чтобы он отправлял shared internal token при reread persisted plan run во время `approve-proposal`.
- Не открывать `POST /api/v1/plan-runs` для internal token-only вызовов; внутреннее исключение нужно только для reread approval artifacts.

### Consequences
- Плюсы: manager review остаётся user-authenticated, а final approval снова работает end-to-end без передачи browser access token через frontend или core payloads.
- Минусы: boundary `core-service -> planner-service` теперь зависит не только от planner snapshot token path, но и от внутреннего read-access правила для persisted plan runs.

## ADR-012: Frontend Token Auth Runtime Uses Same-Origin Core Proxy and In-Memory Access Tokens

- Date: 2026-04-28
- Status: accepted

### Context
Первый frontend shell стартовал с локальным Basic auth workaround, но после появления backend token auth и planner introspection это стало мешать реальному browser flow. Refresh cookie от backend живет на пути `/api/v1/auth/`, поэтому старый dev path `/core-api/api/v1/*` конфликтовал с silent refresh и создавал ложное чувство работоспособности.

### Decision
- Перевести frontend-app на token-based auth flow:
  - `login`, `signup`, `refresh`, `logout`, `me` идут только через `core-service`;
  - access token хранится только в in-memory reactive state frontend-app;
  - refresh token хранится только в HttpOnly cookie backend.
- Для локальной разработки использовать same-origin proxy contract:
  - `/api/*` -> `core-service` без rewrite;
  - `/planner-api/*` -> `planner-service` с rewrite префикса.
- Добавить guest-only auth routes (`/login`, `/signup`) и protected app routes.
- Добавить role-aware navigation и route guards в frontend только как UX-layer; backend RBAC остается единственным permission truth.
- Добавить employee self-service screens для own schedules, schedule days, and leaves вместо попытки расширять manager reference-data screens до всех ролей.

### Consequences
- Плюсы: refresh cookie path совпадает с browser request path, SPA auth flow соответствует backend контрактам, manager/employee UX перестает обещать заведомо запрещенные действия.
- Минусы: access token не переживает закрытие вкладки без refresh cookie; frontend bootstrap теперь зависит от `refresh -> me` и чувствителен к доступности `core-service`.

## ADR-014: Frontend Dev Runtime Is Available in Docker Compose via Vite Container

- Date: 2026-04-29
- Status: accepted

### Context
После завершения frontend Milestone 1 browser shell уже покрывает manager и employee flows, но локальный запуск всё ещё требовал отдельного `npm run dev` вне `docker compose`. Это создавало лишний шаг в onboarding и мешало трактовать `docker compose up --build` как полный dev runtime проекта.

### Decision
- Добавить `frontend-app/Dockerfile` на базе `node:20-alpine`.
- Добавить `frontend-app` service в корневой `docker-compose.yml` и запускать его в dev-режиме через `Vite` на порту `5173`.
- Оставить runtime схему frontend без изменений:
  - `/api/*` проксируется в `core-service`;
  - `/planner-api/*` проксируется в `planner-service`;
  - access token остаётся в памяти браузера;
  - refresh token остаётся в HttpOnly cookie.
- Сохранить standalone host-run (`cd frontend-app && npm run dev`) как допустимую альтернативу для более быстрых локальных UI-итераций.

### Consequences
- Плюсы: `docker compose up --build` теперь поднимает полный full-stack dev runtime, onboarding упрощается, а smoke-проверки можно выполнять без отдельной ручной установки frontend на хосте.
- Минусы: контейнерный dev startup frontend медленнее, чем standalone host-run, и при использовании bind mount + `npm install` на старте возрастает время первого запуска.

## ADR-015: Stage 1 Role Contracts Enrich Frontend Read Models and Add Dual Final Assignment Paths

- Date: 2026-04-30
- Status: accepted

### Context
После завершения frontend Milestone 1 backend Stage 1 уточнил реальные role-aware contracts. Нужно было одновременно:
- стабилизировать frontend bootstrap и lightweight read models;
- ужесточить employee self-scope там, где Milestone 1 UX был слишком широким;
- добавить manual fallback для final assignment без изменения planner boundary.

### Decision
- Возвращать `employee_profile` в `GET /api/v1/auth/me` и в auth payloads `signup`, `login`, `refresh` с полями `id`, `full_name`, `department_id`, `position_name`, `hire_date`, `is_active`.
- Расширить `GET /api/v1/departments/` nested employee summaries, оставив в них только `id`, `full_name`, `position_name` без email.
- Открыть `GET /api/v1/assignments/` для employee в self-scope read-only режиме.
- Добавить explicit backend actions:
  - `POST /api/v1/assignments/manual/`
  - `POST /api/v1/assignments/{id}/reject/`
  - `POST /api/v1/employee-leaves/{id}/set-status/`
- Сузить employee lifecycle rules:
  - schedules и schedule days только `list/retrieve`;
  - employee leave create всегда сохраняет `requested`;
  - employee leave update/delete разрешены только пока статус `requested`;
  - employee не меняет leave status напрямую.
- Для manual assignment создавать сразу final `approved` assignment с `start_date = task.start_date`, `end_date = task.due_date`, `source_plan_run_id = null`.
- Сохранить общий invariant для planner approval и manual assignment: у одной задачи не может появиться второй non-rejected final assignment.
- Не менять `planner-service` и `packages/contracts`; single-task planning по-прежнему идёт через существующий `POST /api/v1/plan-runs` с `task_ids=[task.id]`.

### Consequences
- Плюсы: frontend получает стабильный bootstrap/read-model payload, manager flows получают явную leave-review и manual-assignment опору, а final assignment остаётся backend-owned truth в `core-service`.
- Минусы: Stage 1 backend теперь опережает текущий employee frontend UX, поэтому до следующего frontend slice ожидаемы интеграционные расхождения на schedule/leave/assignment экранах.

## ADR-016: AI Layer Runtime Foundation Uses Local Ollama and Shared pgvector Storage

- Date: 2026-05-05
- Status: accepted

### Context
После стабилизации non-AI MVP понадобилось подготовить минимальную, обратимую foundation для будущего `ai-layer`, не внедряя пока retrieval, explanation APIs и frontend AI UX. Нужно было добавить runtime, который:
- не ломает текущий `core-service`/`planner-service`/`frontend-app` flow;
- не создает новую бизнес-истину;
- готовит shared PostgreSQL к `pgvector` и отдельной AI schema.

### Decision
- Добавить `services/ai-layer` как отдельный FastAPI-сервис в `docker compose` с минимальным `/health` endpoint и env-driven config по образцу `planner-service`.
- Добавить в локальный runtime отдельный контейнер `ollama` для бесплатного локального запуска LLM/embedding моделей.
- Перевести локальный PostgreSQL compose image на вариант с установленным `pgvector`.
- На старте `ai-layer` выполнять bootstrap:
  - `CREATE EXTENSION IF NOT EXISTS vector`
  - `CREATE SCHEMA IF NOT EXISTS ai_layer`
- Использовать тот же PostgreSQL instance, но держать AI-derived storage только в изолированной schema `ai_layer`, без cross-service foreign keys.
- Зарезервировать во frontend dev runtime новый Vite proxy `/ai-api`, не добавляя пока user-facing AI service module или UI.

### Consequences
- Плюсы: появляется стабильная локальная foundation для следующего AI цикла, не меняющая ownership business truth и не требующая отдельной vector DB на MVP-уровне.
- Плюсы: локальный стек с `ollama` и shared `pgvector` можно проверять через `docker compose up --build` без облачных зависимостей.
- Минусы: local runtime становится тяжелее по контейнерам и startup time; `ai-layer` пока не дает user-facing value без следующего цикла retrieval/API/frontend integration.

## ADR-017: AI Layer Reuses Core Introspection and Token-Protected Internal Helper Boundaries

- Date: 2026-05-06
- Status: accepted

### Context
После runtime-bootstrap для `ai-layer` следующая минимальная задача состояла не в retrieval, а в фиксации service boundaries и доступа:
- browser-facing `ai-layer` routes не должны изобретать собственную auth модель;
- `ai-layer` должен видеть только role-allowed frontend calls;
- будущие internal AI reads из `core-service` и `planner-service` должны сразу идти по shared internal token, а не через browser relay.

### Decision
- Повторить в `ai-layer` auth pattern `planner-service`:
  - frontend вызывает `ai-layer` с Bearer token;
  - `ai-layer` валидирует токен через `core-service /api/v1/auth/introspect`;
  - доступ разрешен только ролям `admin` и `manager`.
- Добавить первый frontend-facing authenticated baseline endpoint `GET /api/v1/capabilities` в `ai-layer` для проверки access wiring и runtime metadata.
- Добавить read-only internal AI helper endpoints:
  - `core-service`: `GET /api/v1/internal/ai/service-boundary/`
  - `planner-service`: `GET /api/v1/internal/ai/service-boundary`
- Открывать internal AI helper endpoints только через `X-Internal-Service-Token`.
- Зафиксировать ownership boundary:
  - `core-service` — business truth;
  - `planner-service` — proposals/diagnostics truth;
  - `ai-layer` — retrieval index, explanations, sync metadata.

### Consequences
- Плюсы: auth и role-policy остаются централизованными в `core-service`; `ai-layer` не начинает жить по собственной security-модели.
- Плюсы: следующая итерация retrieval/context endpoints уже имеет готовый internal-only boundary и не потребует browser token relay между backend-сервисами.
- Минусы: `ai-layer` frontend access теперь зависит от доступности `core-service` introspection так же, как и `planner-service`.

## ADR-018: AI Layer Uses Local DTOs, Repository Pattern, and Deferred 503 Explanations

- Date: 2026-05-06
- Status: accepted

### Context
После runtime и auth foundation понадобилось превратить `ai-layer` в реальный backend skeleton, не дожидаясь полного ingestion/retrieval цикла:
- frontend contract для explanation routes уже нужен, чтобы следующий UI slice мог опираться на стабильные endpoint paths и response shape;
- derived AI storage нужно зафиксировать сразу, пока в схеме еще нет исторического мусора и можно безопасно создать `pgvector`-индексы;
- при этом `core-service` и `planner-service` еще не отдают live AI context feeds, поэтому explanation endpoints пока не могут строить полноценные reasoning ответы.

### Decision
- Оставить публичные AI DTO локальными внутри `services/ai-layer`, не выносить их в `packages/contracts` на этом цикле.
- Ввести для `ai-layer` явный application/repository/client split:
  - `app/application/explanations.py`
  - `app/application/reindex.py`
  - `app/infrastructure/repositories/postgres.py`
  - dedicated HTTP clients for `core-service`, `planner-service`, and `ollama`
- Использовать raw `psycopg` repository pattern без ORM и без Alembic в v1.
- Зафиксировать public explanation routes:
  - `POST /api/v1/explanations/assignment-rationale`
  - `POST /api/v1/explanations/unassigned-task`
- Создать derived storage в `ai_layer` schema:
  - `index_items`
  - `sync_state`
  - `explanation_logs`
  - HNSW cosine index over `index_items.embedding`
- Пока retrieval index не заполнен, explanation endpoints возвращают controlled `503` с detail `AI retrieval index is not ready.` вместо пустого `501` или ad-hoc payload.

### Consequences
- Плюсы: следующий retrieval/context cycle получает уже готовый HTTP contract, application service boundary и typed repository API без повторной перестройки маршрутов.
- Плюсы: `ai-layer` может развиваться независимо от `packages/contracts`, пока explanation payloads остаются локальным advisory API, а не shared inter-service contract.
- Минусы: browser-facing explanation endpoints пока дают ограниченную ценность без заполненного индекса и live context ingestion.

## ADR-019: AI Layer Builds V1 Explanations from Internal Feeds, Live Context, and Structured Ollama Output

- Date: 2026-05-07
- Status: accepted

### Context
После skeleton-цикла `ai-layer` уже имел:
- runtime с `ollama` и shared `pgvector`;
- публичные explanation routes;
- локальный repository/application split.

Следующий шаг требовал реальной объяснимости без превращения AI в новый planner:
- retrieval нужно строить только по полезным v1 корпусам, а не по “всем данным системы”;
- browser не должен сам собирать AI context;
- explanation pipeline должен выдерживать деградацию: stale retrieval corpus допустим, stale live context — нет;
- финальное решение об assignment все еще остается за `planner-service` + `core-service`, а не за LLM.

### Decision
- Индексировать только два derived retrieval корпуса:
  - `assignment_case` из `core-service`
  - `unassigned_case` из `planner-service`
- Для `assignment_case` использовать current flattened state:
  - успешные final assignments (`approved`, `active`, `completed`)
  - при переходе assignment в `rejected` или `cancelled` feed возвращает `index_action=delete`
- Не индексировать `employee`, `schedule`, `leave`, `availability_override` как самостоятельный corpus; использовать их только как live context.
- Добавить internal AI feeds и context endpoints:
  - `core-service`
    - `GET /api/v1/internal/ai/index-feed/`
    - `GET /api/v1/internal/ai/tasks/{task_id}/assignment-context/`
  - `planner-service`
    - `GET /api/v1/internal/ai/index-feed`
    - `GET /api/v1/internal/ai/plan-runs/{plan_run_id}/proposal-context`
    - `GET /api/v1/internal/ai/plan-runs/{plan_run_id}/unassigned-context`
- В `ai-layer` строить sync так:
  - full reindex CLI: `python -m app.cli.reindex --mode full`
  - incremental refresh через `changed_since`
  - `refresh_if_stale()` перед explanation
  - если refresh не удался, но старый corpus уже есть, разрешать stale retrieval fallback и явно маркировать это в `advisory_note`
  - если corpus еще не готов, explanation route возвращает `503`
- Для explanation generation использовать:
  - `bge-m3` через `Ollama /api/embed` для feed- и query-embeddings
  - `qwen3:4b` через `Ollama /api/chat`
  - `stream=false`
  - `format=<JSON schema>` для strict structured output
- Публичный response shape не менять:
  - `summary`
  - `reasons[]`
  - `risks[]`
  - `recommended_actions[]`
  - `similar_cases[]`
  - `advisory_note`

### Consequences
- Плюсы: manager-facing explanation flow теперь строится на backend-owned data boundaries и historical retrieval, а не на browser-assembled payloads.
- Плюсы: retrieval corpus остается маленьким и объяснимым; векторный поиск не начинает дублировать всю operational DB.
- Плюсы: stale fallback ограничен только derived corpus и не размывает live context truth из `core-service`/`planner-service`.
- Минусы: explanation качество зависит от локального `ollama` runtime и может деградировать при недоступности модели или плохом structured output.
- Минусы: `assignment_case` в v1 — это current flattened view, а не отдельное historical snapshot-хранилище, поэтому объяснения чувствительны к последующим изменениям task/employee state.
