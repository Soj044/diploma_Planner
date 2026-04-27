"""HTTP API planner-service для запуска и чтения расчетов назначений.

Этот файл принимает команду на создание plan run и отдает persisted proposals
для manager review. Он связывает FastAPI routes с application service,
snapshot client и planner artifact repository.
"""

from fastapi import APIRouter, HTTPException

from contracts.schemas import CreatePlanRunRequest, PlanResponse

from app.application.plan_runs import PlanRunService
from app.application.snapshot_client import SnapshotClientError
from app.config import CORE_SERVICE_URL, INTERNAL_SERVICE_TOKEN, PLANNER_DB_PATH
from app.infrastructure.clients.core_service import CoreServiceSnapshotClient
from app.infrastructure.repositories.sqlite import SqlitePlanRunRepository

router = APIRouter(prefix="/api/v1/plan-runs", tags=["plan-runs"])
repository = SqlitePlanRunRepository(db_path=PLANNER_DB_PATH)
snapshot_client = CoreServiceSnapshotClient(
    base_url=CORE_SERVICE_URL,
    internal_service_token=INTERNAL_SERVICE_TOKEN,
)
service = PlanRunService(repository=repository, snapshot_client=snapshot_client)


@router.post("", response_model=PlanResponse)
def create_plan_run(payload: CreatePlanRunRequest) -> PlanResponse:
    try:
        return service.create(payload)
    except SnapshotClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{plan_run_id}", response_model=PlanResponse)
def get_plan_run(plan_run_id: str) -> PlanResponse:
    run = service.get(plan_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Plan run not found")
    return run
