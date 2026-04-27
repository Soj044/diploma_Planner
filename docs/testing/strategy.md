# Testing Strategy

## Priorities
- core-service model constraints and CRUD smoke tests
- core-service planning snapshot export and internal planner access
- eligibility logic
- scoring logic
- planning constraints
- planner artifact persistence and retrieval
- assignment approval flow
- shared contracts validation for planning windows and proposal dates

## Basic checks
- core-service: local startup, migration workflow, authenticated CRUD smoke tests, model constraints, serializer validation, planning snapshot export for authenticated users and internal token calls
- core-service approval flow: persisted planner proposal lookup, idempotent replay for the same `task + employee + source_plan_run_id`, rejection of missing or non-selected proposals, rejection of second final assignment for one task, upstream planner failure handling
- planner-service: unit and integration tests for planning pipeline, `CreatePlanRunRequest` boundary, snapshot client failure handling, SQLite persistence of run/snapshot/proposals/unassigned/solver stats, persisted run retrieval for manager review, overlap conflict diagnostics, and weighted score stability
- frontend-app: install dependencies, type-check the Vue shell, build production bundle, and manually verify routing/navigation plus env-driven backend configuration cards
- contracts: schema compatibility between services

## Suggested MVP Commands

```bash
# Core service
cd services/core-service
poetry install
poetry run python manage.py makemigrations --check
poetry run python manage.py check
poetry run python manage.py migrate
poetry run python manage.py test

# Core service quick unit checks without a local PostgreSQL container
DJANGO_TEST_SQLITE=true poetry run python manage.py test

# Planner service
cd services/planner-service
poetry install
poetry run pytest -q

# Frontend app
cd frontend-app
npm install
npm run type-check
npm run build

# Container smoke
cd /path/to/repo
docker compose up --build
```

## Frontend Manual Smoke

- Start backend services and the frontend shell locally.
- Open `http://localhost:5173`.
- Verify sidebar navigation works for `Shell`, `Reference Data`, `Tasks`, `Planning`, and `Assignments`.
- Verify the runtime configuration card shows the expected `core-service` and `planner-service` URLs from `.env.local`.
- Verify the shell clearly shows the current auth assumption instead of pretending a login flow already exists.
- On `Reference Data`, verify authenticated list/create/edit/delete for `users`, `departments`, `skills`, and `employees`.
- Verify employee creation only offers free `users` or the user already linked to the employee being edited.
- On `Tasks`, verify authenticated list/create/edit/delete for `tasks` and `task-requirements`.
- Verify selecting `Requirements` on a task focuses the requirement editor on that task.
- Verify task validation errors from backend are surfaced unchanged, especially invalid `start_date > due_date`.
