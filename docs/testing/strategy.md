# Testing Strategy

## Priorities
- eligibility logic
- scoring logic
- planning constraints
- assignment approval flow

## Basic checks
- core-service: local startup and migration workflow
- planner-service: unit and integration tests for planning pipeline
- contracts: schema compatibility between services

## Suggested MVP Commands

```bash
# Core service
cd services/core-service
poetry install
poetry run python manage.py makemigrations --check
poetry run python manage.py migrate
poetry run python manage.py test

# Planner service
cd services/planner-service
poetry install
poetry run pytest -q

# Container smoke
cd /path/to/repo
docker compose up --build
```
