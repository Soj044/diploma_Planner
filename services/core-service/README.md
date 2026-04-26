# core-service

Django + DRF сервис с бизнес-сущностями и хранением final approved assignments.

## Конфигурация

Настройки читаются из `services/core-service/.env` (или из переменных контейнера).
Ключевые переменные:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `INTERNAL_SERVICE_TOKEN`
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

## Approval handoff

`POST /api/v1/assignments/approve-proposal/` creates an approved core `Assignment`
from a selected persisted planner proposal. The request accepts:
- `task`
- `employee`
- `source_plan_run_id`
- optional `notes`

During approval, `core-service` reads the persisted planner run from `planner-service`,
re-validates the requested proposal, keeps the operation idempotent for the same
`task + employee + source_plan_run_id`, and writes the final `Assignment` plus
`AssignmentChangeLog` in the core database. Planner proposals remain artifacts only.

## Planner snapshot boundary

`POST /api/v1/planning-snapshot/` exports a planner-ready `PlanningSnapshot` from
core business truth. The endpoint accepts either:
- an authenticated core user request
- an internal service request with `X-Internal-Service-Token`
