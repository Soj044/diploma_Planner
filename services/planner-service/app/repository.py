"""In-memory persistence for planner run artifacts in MVP."""

from collections.abc import Mapping
from datetime import datetime, timezone

from contracts.schemas import PlanResponse


class PlanRunRepository:
    """Stores planner outputs in-memory for MVP and local development."""

    def __init__(self) -> None:
        self._runs: dict[str, PlanResponse] = {}

    def save(self, response: PlanResponse) -> None:
        self._runs[response.summary.plan_run_id] = response

    def get(self, plan_run_id: str) -> PlanResponse | None:
        return self._runs.get(plan_run_id)

    def list_runs(self) -> Mapping[str, PlanResponse]:
        return self._runs


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)
