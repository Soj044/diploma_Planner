"""Точка входа planner-service для расчета, чтения и internal helper routes.

Этот файл собирает FastAPI-приложение, подключает routes plan runs и публикует
health endpoint. Через него planner-service отдает proposals для review,
предоставляет token-protected internal AI helper routes и использует внутренние
planning/application модули.
"""

from fastapi import FastAPI

from app.api.internal_ai import router as internal_ai_router
from app.api.plan_runs import router as plan_runs_router

app = FastAPI(title="planner-service", version="0.1.0")
app.include_router(plan_runs_router)
app.include_router(internal_ai_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
