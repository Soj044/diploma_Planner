"""In-memory planner artifact repository for MVP and local development."""

from dataclasses import dataclass
from hashlib import sha256

from contracts.schemas import AssignmentProposal, PlanResponse, PlanningSnapshot, UnassignedTaskDiagnostic


@dataclass(frozen=True)
class PlanRunRecord:
    plan_run_id: str
    snapshot: PlanningSnapshot
    source_hash: str
    proposals: list[AssignmentProposal]
    unassigned: list[UnassignedTaskDiagnostic]
    solver_statistics: dict[str, int | float | str]
    response: PlanResponse


class InMemoryPlanRunRepository:
    """Stores MVP planner artifacts without introducing a planner database yet."""

    def __init__(self) -> None:
        self._records: dict[str, PlanRunRecord] = {}

    def save(self, snapshot: PlanningSnapshot, response: PlanResponse) -> None:
        plan_run_id = response.summary.plan_run_id
        self._records[plan_run_id] = PlanRunRecord(
            plan_run_id=plan_run_id,
            snapshot=snapshot,
            source_hash=self._source_hash(snapshot),
            proposals=response.proposals,
            unassigned=response.unassigned,
            solver_statistics=response.artifacts.solver_statistics,
            response=response,
        )

    def get(self, plan_run_id: str) -> PlanResponse | None:
        record = self._records.get(plan_run_id)
        if record is None:
            return None
        return record.response

    def list_records(self) -> dict[str, PlanRunRecord]:
        return dict(self._records)

    def _source_hash(self, snapshot: PlanningSnapshot) -> str:
        return sha256(snapshot.model_dump_json().encode("utf-8")).hexdigest()
