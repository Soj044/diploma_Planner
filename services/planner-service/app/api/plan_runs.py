"""HTTP API planner-service для запуска и чтения расчетов назначений.

Этот файл принимает команду на создание plan run и отдает persisted proposals
для manager review. Он связывает FastAPI routes с application service,
snapshot client и planner artifact repository.
"""

from fastapi import APIRouter, Depends, Header, HTTPException

from contracts.schemas import CreatePlanRunRequest, PlanResponse

from app.application.plan_runs import PlanRunService
from app.application.snapshot_client import SnapshotClientError
from app.config import CORE_SERVICE_URL, INTERNAL_SERVICE_TOKEN, PLANNER_DB_PATH
from app.infrastructure.clients.core_service import (
    AuthenticatedUserContext,
    CoreServiceAuthClient,
    CoreServiceAuthError,
    CoreServiceSnapshotClient,
)
from app.infrastructure.repositories.sqlite import SqlitePlanRunRepository

router = APIRouter(prefix="/api/v1/plan-runs", tags=["plan-runs"])
repository = SqlitePlanRunRepository(db_path=PLANNER_DB_PATH)
snapshot_client = CoreServiceSnapshotClient(
    base_url=CORE_SERVICE_URL,
    internal_service_token=INTERNAL_SERVICE_TOKEN,
)
auth_client = CoreServiceAuthClient(
    base_url=CORE_SERVICE_URL,
    internal_service_token=INTERNAL_SERVICE_TOKEN,
)
service = PlanRunService(repository=repository, snapshot_client=snapshot_client)


def require_planner_access(authorization: str | None = Header(default=None)) -> AuthenticatedUserContext:
    """Allow planner runs only for admin and manager users with valid tokens."""

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Bearer access token is required.")

    try:
        context = auth_client.introspect_access_token(token.strip())
    except CoreServiceAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if not context.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive.")
    if context.role not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="You do not have access to planner runs.")
    return context


@router.post("", response_model=PlanResponse)
def create_plan_run(
    payload: CreatePlanRunRequest,
    _: AuthenticatedUserContext = Depends(require_planner_access),
) -> PlanResponse:
    try:
        return service.create(payload)
    except SnapshotClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{plan_run_id}", response_model=PlanResponse)
def get_plan_run(
    plan_run_id: str,
    _: AuthenticatedUserContext = Depends(require_planner_access),
) -> PlanResponse:
    run = service.get(plan_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Plan run not found")
    return run
