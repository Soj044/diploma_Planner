"""Application use cases for planner runs."""

from contracts.schemas import CreatePlanRunRequest, PlanResponse

from app.application.snapshot_client import SnapshotClient
from app.planning.runner import run_planning
from app.repositories.plan_runs import PlanRunRepository


class PlanRunService:
    """Coordinates planning execution and artifact persistence."""

    def __init__(self, repository: PlanRunRepository, snapshot_client: SnapshotClient) -> None:
        self._repository = repository
        self._snapshot_client = snapshot_client

    def create(self, request: CreatePlanRunRequest) -> PlanResponse:
        snapshot = self._snapshot_client.fetch_snapshot(request)
        response = run_planning(snapshot)
        self._repository.save(snapshot=snapshot, response=response)
        return response

    def get(self, plan_run_id: str) -> PlanResponse | None:
        return self._repository.get(plan_run_id)
