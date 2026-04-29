# core-service

Django + DRF сервис с бизнес-сущностями и хранением final approved assignments.

## Конфигурация

Настройки читаются из `services/core-service/.env` (или из переменных контейнера).
Ключевые переменные:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `INTERNAL_SERVICE_TOKEN`
- `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`
- `JWT_REFRESH_TOKEN_LIFETIME_DAYS`
- `JWT_REFRESH_COOKIE_NAME`
- `JWT_REFRESH_COOKIE_SECURE`
- `JWT_REFRESH_COOKIE_SAMESITE`
- `JWT_REFRESH_COOKIE_PATH`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

## Запуск

```bash
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver 0.0.0.0:8000
```

Для быстрых unit-проверок без локального PostgreSQL контейнера:

```bash
DJANGO_TEST_SQLITE=true poetry run python manage.py test
```

## Сущности MVP

- User
- Department, Skill, Employee, EmployeeSkill
- WorkSchedule, WorkScheduleDay
- EmployeeLeave, EmployeeAvailabilityOverride
- Task, TaskRequirement
- Assignment, AssignmentChangeLog

## Структура приложений

- `users` — кастомная модель пользователя и роли MVP.
- `operations` — бизнес-сущности и простой DRF CRUD для MVP.

## Auth endpoints

Token auth for API:
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/introspect` (internal service use)

Flow:
- Access token is returned in JSON.
- Refresh token is stored in HttpOnly cookie.
- Django session auth remains available for `/admin/`.

## User-Employee sync

- Users with role `manager` or `employee` receive an auto-created `Employee` profile if missing.
- Role change from `admin` to `manager/employee` also auto-creates profile if needed.
- Role change to `admin` does not delete an existing profile.

## RBAC policy

- `admin`: full CRUD access including users and role management endpoints.
- `manager`: operational access for tasks, schedules, overrides, approvals, and read access where required.
- `employee`: read-only tasks plus self-scope CRUD for own schedules and leaves.
- `planning-snapshot` is internal-only via `X-Internal-Service-Token`.

## Approval handoff

`POST /api/v1/assignments/approve-proposal/` creates an approved core `Assignment`
from a selected persisted planner proposal. The request accepts:
- `task`
- `employee`
- `source_plan_run_id`
- optional `notes`

During approval, `core-service` reads the persisted planner run from `planner-service`,
using the shared `INTERNAL_SERVICE_TOKEN`,
re-validates the requested proposal, keeps the operation idempotent for the same
`task + employee + source_plan_run_id`, and writes the final `Assignment` plus
`AssignmentChangeLog` in the core database. Planner proposals remain artifacts only.

## Planner snapshot boundary

`POST /api/v1/planning-snapshot/` exports a planner-ready `PlanningSnapshot` from
core business truth. The endpoint accepts either:
- an authenticated core user request
- an internal service request with `X-Internal-Service-Token`
