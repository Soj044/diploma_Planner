from datetime import date, datetime, timezone

import pytest

from contracts.schemas import CreatePlanRunRequest, EmployeeAvailability, EmployeeSnapshot, PlanningSnapshot, TaskSnapshot

from app.application.plan_runs import PlanRunService
from app.application.snapshot_client import SnapshotClientError
from app.infrastructure.repositories.in_memory import InMemoryPlanRunRepository


class FakeSnapshotClient:
    def __init__(self, snapshot: PlanningSnapshot) -> None:
        self.snapshot = snapshot
        self.requests: list[CreatePlanRunRequest] = []

    def fetch_snapshot(self, request: CreatePlanRunRequest) -> PlanningSnapshot:
        self.requests.append(request)
        return self.snapshot


class FailingSnapshotClient:
    def fetch_snapshot(self, request: CreatePlanRunRequest) -> PlanningSnapshot:
        raise SnapshotClientError("core-service is unavailable for planning snapshot fetch")


def build_request() -> CreatePlanRunRequest:
    return CreatePlanRunRequest(
        planning_period_start=date(2026, 3, 23),
        planning_period_end=date(2026, 3, 23),
        initiated_by_user_id="manager-1",
        department_id="dep-1",
    )


def build_snapshot() -> PlanningSnapshot:
    return PlanningSnapshot(
        planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
        planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
        employees=[
            EmployeeSnapshot(
                employee_id="emp-1",
                department_id="dep-1",
                availability=[
                    EmployeeAvailability(
                        start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                        end_at=datetime(2026, 3, 23, 16, 0, tzinfo=timezone.utc),
                        available_hours=8,
                    )
                ],
            )
        ],
        tasks=[
            TaskSnapshot(
                task_id="task-1",
                department_id="dep-1",
                title="Pack boxes",
                starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
                estimated_hours=3,
            )
        ],
    )


def test_plan_run_service_fetches_snapshot_and_persists_artifacts() -> None:
    request = build_request()
    snapshot = build_snapshot()
    repository = InMemoryPlanRunRepository()
    snapshot_client = FakeSnapshotClient(snapshot)
    service = PlanRunService(repository=repository, snapshot_client=snapshot_client)

    response = service.create(request)

    assert snapshot_client.requests == [request]
    stored_record = repository.list_records()[response.summary.plan_run_id]
    assert stored_record.snapshot == snapshot
    assert response.summary.assigned_count == 1
    assert response.summary.planning_period_start == snapshot.planning_period_start


def test_plan_run_service_does_not_persist_when_snapshot_fetch_fails() -> None:
    repository = InMemoryPlanRunRepository()
    service = PlanRunService(repository=repository, snapshot_client=FailingSnapshotClient())

    with pytest.raises(SnapshotClientError, match="core-service is unavailable"):
        service.create(build_request())

    assert repository.list_records() == {}
