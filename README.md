# Workestrator Monorepo

Дипломный MVP для автоматизированного операционного планирования и назначения задач.

## Что входит в репозиторий

- `services/core-service` — Django + DRF, источник бизнес-истины
- `services/planner-service` — FastAPI + OR-Tools/CP-SAT, persisted `plan runs`, `proposals`, `diagnostics`
- `frontend-app` — Vue 3 + Vite thin client для manager и employee flows
- `packages/contracts` — общий слой DTO/контрактов между сервисами

## Что уже реализовано

- CRUD по основным справочникам и доменным сущностям в `core-service`
- token auth flow: `signup`, `login`, `refresh`, `logout`, `me`
- RBAC для `admin`, `manager`, `employee`
- запуск planning run через `planner-service`
- persisted review proposals и diagnostics
- manager approval flow через `POST /api/v1/assignments/approve-proposal/`
- employee self-service для своих schedules и leaves

## Что еще не реализовано

- read-only экран итоговых assignments во frontend
- AI/RAG слой
- сложные уведомления, realtime и внешние интеграции

## Требования

- Docker + Docker Compose
- Node.js 18+
- npm

## Быстрый запуск всего проекта

### 1. Подготовить переменные окружения

Из корня репозитория:

```bash
cp .env.example .env
```

Текущий `.env.example` уже достаточен для локального MVP запуска.

### 2. Поднять backend и базу

```bash
docker compose up --build
```

После старта будут доступны:

- `core-service`: `http://localhost:8000/api/v1/`
- `Django admin`: `http://localhost:8000/admin/`
- `planner-service health`: `http://localhost:8001/health`
- `planner-service docs`: `http://localhost:8001/docs`

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

### 4. Поднять frontend

В отдельном терминале:

```bash
cd frontend-app
cp .env.example .env.local
npm install
npm run dev
```

Frontend будет доступен по адресу:

- `http://localhost:5173`

### 5. Открыть приложение

Начальная точка для защищенного frontend flow:

- `http://localhost:5173/login`

Публичная employee-регистрация:

- `http://localhost:5173/signup`

## Как работает frontend runtime

- `core-service` вызывается через `/api/v1/*`
- auth endpoints вызываются через `/api/v1/auth/*`
- `planner-service` вызывается через `/planner-api/api/v1/*`
- Vite proxy нужен только для локальной разработки
- refresh token хранится в HttpOnly cookie
- access token хранится только в памяти frontend

Важно:

- frontend больше не использует Basic auth workaround
- для локальной разработки backend должен быть поднят до открытия UI

## Минимальный ручной сценарий проверки

### Manager/admin flow

1. Зайти в `http://localhost:5173/login`
2. Войти пользователем с ролью `manager` или `admin`
3. Открыть `Reference Data` и создать нужные справочники
4. Открыть `Tasks` и создать задачу с requirements
5. Открыть `Planning`
6. Запустить `plan run`
7. Перезагрузить persisted run по `plan_run_id`
8. Выбрать selected proposal и выполнить approval

### Employee flow

1. Открыть `http://localhost:5173/signup`
2. Создать employee account
3. Убедиться, что доступны только `Tasks`, `My Schedule`, `My Leaves`
4. Проверить CRUD только для собственных schedules и leaves

## Полезные URLs

- `core-service API root`: `http://localhost:8000/api/v1/`
- `core-service admin`: `http://localhost:8000/admin/`
- `planner-service docs`: `http://localhost:8001/docs`
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

### frontend-app

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
```

## Документация

- общий индекс: `docs/README.md`
- архитектура: `docs/architecture/overview.md`
- решения: `docs/architecture/decisions.md`
- testing: `docs/testing/strategy.md`
- frontend backlog: `docs/frontend-backlog.md`
