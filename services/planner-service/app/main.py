"""FastAPI entrypoint for planner-service MVP."""

from fastapi import FastAPI

from app.api.plan_runs import router as plan_runs_router

app = FastAPI(title="planner-service", version="0.1.0")
app.include_router(plan_runs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
