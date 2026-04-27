# Workestrator Monorepo (MVP)

Дипломный проект: автоматизированное операционное планирование и назначение задач.

## Сервисы

- `services/core-service` — Django + DRF, источник бизнес-истины.
- `services/planner-service` — FastAPI + OR-Tools/CP-SAT, расчет предложений по назначениям.
- `frontend-app` — Vue 3 + Vite thin client для manager-facing MVP flows.
- `packages/contracts` — общий слой DTO/схем между сервисами.
- `services/ai-layer` — future-only слой, без реализации в MVP.

## Границы MVP

В MVP включено:
- CRUD по ключевым сущностям core-domain.
- Запуск `plan-run` и генерация `proposals` в planner-service.
- Базовая explainability через diagnostics по неназначенным задачам.
- Docker-запуск двух сервисов + PostgreSQL.

В MVP не включено:
- frontend;
- RAG/LLM и любые AI-зависимости;
- сложные fairness/soft-constraint профили.

## Локальный запуск через Docker

1. Скопировать переменные окружения:
```bash
cp .env.example .env
```

2. Поднять сервисы:
```bash
docker compose up --build
```

3. Проверить health:
- core-service: `http://localhost:8000/api/v1/`
- planner-service: `http://localhost:8001/health`

4. Поднять frontend shell локально:
```bash
cd frontend-app
cp .env.example .env.local
npm install
npm run dev
```

- frontend-app: `http://localhost:5173`

## Локальная разработка через Poetry

```bash
cd services/core-service
poetry install

cd ../planner-service
poetry install
```

## Frontend локальная разработка

```bash
cd frontend-app
npm install
npm run dev
```

Первый frontend slice использует Vite proxy (`/core-api`, `/planner-api`) и не добавляет отдельный auth flow.
Для локального MVP доступа к `core-service` можно передать Basic credentials через `frontend-app/.env.local`.
