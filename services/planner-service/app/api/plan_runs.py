"""Plan run API routes."""

from fastapi import APIRouter, HTTPException

from contracts.schemas import PlanRequest, PlanResponse

from app.application.plan_runs import PlanRunService
from app.infrastructure.repositories.in_memory import InMemoryPlanRunRepository

router = APIRouter(prefix="/api/v1/plan-runs", tags=["plan-runs"])
repository = InMemoryPlanRunRepository()
service = PlanRunService(repository=repository)


@router.post("", response_model=PlanResponse)
def create_plan_run(payload: PlanRequest) -> PlanResponse:
    return service.create_from_snapshot(payload)


@router.get("/{plan_run_id}", response_model=PlanResponse)
def get_plan_run(plan_run_id: str) -> PlanResponse:
    run = service.get(plan_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Plan run not found")
    return run
