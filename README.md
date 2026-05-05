# Workestrator Monorepo

Дипломный MVP для автоматизированного операционного планирования и назначения задач.

## Что входит в репозиторий

- `services/core-service` — Django + DRF, источник бизнес-истины
- `services/planner-service` — FastAPI + OR-Tools/CP-SAT, persisted `plan runs`, `proposals`, `diagnostics`
- `services/ai-layer` — FastAPI bootstrap для будущего AI support layer, локальный `ollama`, shared `pgvector` foundation
- `frontend-app` — Vue 3 + Vite thin client для manager и employee flows
- `packages/contracts` — общий слой DTO/контрактов между сервисами

## Что уже реализовано

- CRUD по основным справочникам и доменным сущностям в `core-service`
- token auth flow: `signup`, `login`, `refresh`, `logout`, `me`
- RBAC для `admin`, `manager`, `employee`
- запуск planning run через `planner-service`
- persisted review proposals и diagnostics
- manager approval flow через `POST /api/v1/assignments/approve-proposal/`
- manual assignment flow через `POST /api/v1/assignments/manual/`
- employee canonical UX:
- assignment-first `Tasks`
- read-only `Schedule`
- requested-only `Leaves`
- `Departments`
- `Profile`
- manager/admin canonical UX:
- top navigation
- own `Tasks` workspace
- `/tasks/new` create-and-assign wizard
- employee schedule management
- requested leave review queue
- read-only экран итоговых assignments
- admin users/roles workspace
- AI runtime foundation:
- `ai-layer` health/bootstrap service
- `ollama` container in local compose runtime
- shared PostgreSQL `pgvector` + `ai_layer` schema bootstrap

## Что еще не реализовано

- frontend-facing AI/RAG retrieval and explanation flows
- сложные уведомления, realtime и внешние интеграции

## Требования

- Docker + Docker Compose
- Node.js 18+ и npm только если ты хочешь запускать `frontend-app` вне Docker

## Быстрый запуск всего проекта

### 1. Подготовить переменные окружения

Из корня репозитория:

```bash
cp .env.example .env
```

Текущий `.env.example` уже достаточен для локального MVP запуска, включая foundation для `ai-layer`, `ollama` и shared `pgvector` storage.

### 2. Поднять весь dev runtime

```bash
docker compose up --build
```

После старта будут доступны:

- `core-service`: `http://localhost:8000/api/v1/`
- `Django admin`: `http://localhost:8000/admin/`
- `planner-service health`: `http://localhost:8001/health`
- `planner-service docs`: `http://localhost:8001/docs`
- `ai-layer health`: `http://localhost:8002/health`
- `ollama API`: `http://localhost:11434/api/tags`
- `frontend-app`: `http://localhost:5173`

Если `core-service` падает с `InconsistentMigrationHistory`, значит локальный `postgres_data` volume остался от более старой схемы. Для чистого MVP-старта:

```bash
docker compose down -v
docker compose up --build
```

Это удалит локальные контейнерные данные PostgreSQL и пересоздаст БД заново.

По умолчанию `core-service` теперь запускается через `python manage.py safe_migrate`.
Если при старом локальном volume обнаруживается `InconsistentMigrationHistory`, сервис автоматически
сбрасывает `public` schema в локальном PostgreSQL контейнере и повторяет миграции.
Отключить этот recovery можно переменной:

```bash
CORE_DB_AUTO_RESET_ON_INCONSISTENT_MIGRATIONS=false
```

### 3. Создать пользователя для manager/admin flows

Публичный `signup` во frontend создает только `employee` account.
Для manager/admin сценариев нужен пользователь с нужной ролью.

Создай superuser:

```bash
docker exec -it workestrator-core python manage.py createsuperuser
```

Потом:

1. открой `http://localhost:8000/admin/`
2. зайди под созданным superuser
3. открой пользователя и при необходимости выставь `role` в `admin` или `manager`

Если нужен обычный employee-пользователь, его можно создать прямо из frontend через `signup`.

### 4. Открыть frontend

- `http://localhost:5173/login`
- `http://localhost:5173/signup`

## Альтернативный запуск frontend вне Docker

Если удобнее работать с `frontend-app` напрямую на хосте:

```bash
cd frontend-app
cp .env.example .env.local
npm install
npm run dev
```

В этом режиме:

- backend всё равно должен быть поднят через `docker compose up --build`
- frontend тоже будет доступен на `http://localhost:5173`

### 5. Открыть приложение

Начальная точка для защищенного frontend flow:

- `http://localhost:5173/login`

Публичная employee-регистрация:

- `http://localhost:5173/signup`

## Как работает frontend runtime

- `core-service` вызывается через `/api/v1/*`
- auth endpoints вызываются через `/api/v1/auth/*`
- `planner-service` вызывается через `/planner-api/api/v1/*`
- будущие frontend-facing AI routes будут вызываться через `/ai-api/api/v1/*`
- Vite proxy используется и в standalone-режиме, и внутри `frontend-app` container
- refresh token хранится в HttpOnly cookie
- access token хранится только в памяти frontend

Важно:

- frontend больше не использует Basic auth workaround
- при запуске через `docker compose` frontend автоматически проксирует `core-service`, `planner-service` и зарезервированный `ai-layer` runtime path по именам compose-сервисов
- при standalone-запуске frontend использует `localhost` proxy targets из `frontend-app/.env.example`

## Минимальный ручной сценарий проверки

### Manager/admin flow

1. Зайти в `http://localhost:5173/login`
2. Войти пользователем с ролью `manager` или `admin`
3. Открыть `Admin` и создать нужные справочники
4. Открыть `Tasks` и создать задачу с requirements
5. Открыть `http://localhost:5173/planning`
6. Запустить `plan run`
7. Перезагрузить persisted run по `plan_run_id`
8. Выбрать selected proposal и выполнить approval
9. Открыть `http://localhost:5173/assignments` и проверить, что final `Assignment` появился в read-only списке

`Planning` и `Assignments` сохранены как совместимые advanced routes, но после Stage 2 больше не показываются в основном верхнем меню.

### Employee flow

1. Открыть `http://localhost:5173/signup`
2. Создать employee account
3. Убедиться, что в верхнем меню доступны `Tasks`, `Schedule`, `Leaves`, `Departments`, `Profile`
4. Убедиться, что `Profile` рендерится из auth session payload
5. Учесть, что `Schedule`, `Leaves` и `Departments` после Stage 2 пока закреплены как canonical routes и scaffold screens до следующего frontend slice

## Полезные URLs

- `core-service API root`: `http://localhost:8000/api/v1/`
- `core-service admin`: `http://localhost:8000/admin/`
- `planner-service docs`: `http://localhost:8001/docs`
- `ai-layer health`: `http://localhost:8002/health`
- `ollama API`: `http://localhost:11434/api/tags`
- `frontend-app`: `http://localhost:5173`

## Локальная разработка по сервисам

### core-service

```bash
cd services/core-service
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver 0.0.0.0:8000
```

Быстрая локальная проверка без PostgreSQL контейнера:

```bash
cd services/core-service
DJANGO_TEST_SQLITE=true poetry run python manage.py test
```

### planner-service

```bash
cd services/planner-service
poetry install
poetry run pytest -q
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### ai-layer

```bash
cd services/ai-layer
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8002
```

При старте `ai-layer` сам проверяет доступность PostgreSQL, включает `CREATE EXTENSION IF NOT EXISTS vector` и создает отдельную schema `ai_layer`.

### frontend-app

Через Docker Compose:

```bash
docker compose up --build frontend-app
```

Или напрямую на хосте:

```bash
cd frontend-app
npm install
npm run type-check
npm run build
npm run dev
```

## Базовые verification команды

```bash
# frontend
cd frontend-app
npm run type-check
npm run build

# core-service
cd services/core-service
DJANGO_TEST_SQLITE=true poetry run python manage.py test

# planner-service
cd services/planner-service
poetry run pytest -q

# ai-layer bootstrap smoke
curl http://localhost:8002/health
```

## Документация

- общий индекс: `docs/README.md`
- архитектура: `docs/architecture/overview.md`
- решения: `docs/architecture/decisions.md`
- testing: `docs/testing/strategy.md`
- frontend backlog: `docs/frontend-backlog.md`
