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
        """Build a snapshot, run planning, and persist the resulting artifacts."""

        snapshot = self._snapshot_client.fetch_snapshot(request)
        response = run_planning(snapshot)
        self._repository.save(command=request, snapshot=snapshot, response=response)
        return response

    def get(self, plan_run_id: str) -> PlanResponse | None:
        """Return a persisted plan run by its public UUID."""

        return self._repository.get(plan_run_id)
