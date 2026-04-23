"""Application use cases for planner runs."""

from contracts.schemas import PlanResponse, PlanningSnapshot

from app.planning.runner import run_planning
from app.repositories.plan_runs import PlanRunRepository


class PlanRunService:
    """Coordinates planning execution and artifact persistence."""

    def __init__(self, repository: PlanRunRepository) -> None:
        self._repository = repository

    def create_from_snapshot(self, snapshot: PlanningSnapshot) -> PlanResponse:
        response = run_planning(snapshot)
        self._repository.save(snapshot=snapshot, response=response)
        return response

    def get(self, plan_run_id: str) -> PlanResponse | None:
        return self._repository.get(plan_run_id)
