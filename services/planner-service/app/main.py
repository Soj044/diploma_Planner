"""FastAPI entrypoint for planner-service MVP."""

from fastapi import FastAPI, HTTPException

from contracts.schemas import PlanRequest, PlanResponse

from .planning import run_planning
from .repository import PlanRunRepository

app = FastAPI(title="planner-service", version="0.1.0")
repo = PlanRunRepository()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/plan-runs", response_model=PlanResponse)
def create_plan_run(payload: PlanRequest) -> PlanResponse:
    response = run_planning(payload)
    repo.save(response)
    return response


@app.get("/api/v1/plan-runs/{plan_run_id}", response_model=PlanResponse)
def get_plan_run(plan_run_id: str) -> PlanResponse:
    run = repo.get(plan_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Plan run not found")
    return run
