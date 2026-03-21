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
python manage.py makemigrations --check
python manage.py migrate
python manage.py test

# Planner service
cd services/planner-service
pytest -q
```
