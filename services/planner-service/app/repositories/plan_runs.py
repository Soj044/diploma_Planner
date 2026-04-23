"""Repository boundary for planner run artifacts."""

from typing import Protocol

from contracts.schemas import PlanResponse, PlanningSnapshot


class PlanRunRepository(Protocol):
    def save(self, snapshot: PlanningSnapshot, response: PlanResponse) -> None:
        """Persist a finished plan run and its MVP artifacts."""

    def get(self, plan_run_id: str) -> PlanResponse | None:
        """Return a saved plan run response by public run id."""
