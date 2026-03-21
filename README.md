# Workestrator Monorepo (MVP)

Дипломный проект: автоматизированное операционное планирование и назначение задач.

## Сервисы

- `services/core-service` — Django + DRF, источник бизнес-истины.
- `services/planner-service` — FastAPI + OR-Tools/CP-SAT, расчет предложений по назначениям.
- `packages/contracts` — общий слой DTO/схем между сервисами.
- `ai-layer` — в будущем, сейчас не реализуется.

## Границы MVP

В MVP включено:
- CRUD по ключевым сущностям core-domain.
- Запуск planning-run и генерация proposals в planner-service.
- Базовая explainability через diagnostics по неназначенным задачам.

В MVP не включено:
- frontend;
- RAG/LLM и любые AI-зависимости;
- сложные fairness/soft-constraint профили.

## Минимальная структура

```text
services/
  core-service/
  planner-service/
packages/
  contracts/
docs/
```

## Быстрый старт (локально)

1. Core service:
```bash
cd services/core-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

2. Planner service:
```bash
cd services/planner-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

3. Контракты:
```bash
pip install -e packages/contracts
```

## Порядок реализации

1. `core-service` (стабилизация доменной истины и approval flow).
2. `planner-service` (snapshot -> eligibility -> scoring -> CP-SAT -> proposals).
3. AI-слой после MVP.
