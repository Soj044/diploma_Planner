# core-service

Django + DRF сервис с бизнес-сущностями и хранением final approved assignments.

## Конфигурация

Настройки читаются из `services/core-service/.env` (или из переменных контейнера).
Ключевые переменные:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

## Запуск

```bash
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver 0.0.0.0:8000
```

## Сущности MVP

- Department, Skill, Employee, EmployeeSkill
- WorkSchedule, WorkScheduleDay
- EmployeeLeave, EmployeeAvailabilityOverride
- Task, TaskRequirement
- Assignment, AssignmentChangeLog
