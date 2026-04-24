from datetime import datetime, timezone

from contracts.schemas import EmployeeAvailability, EmployeeSnapshot, PlanningSnapshot, TaskSnapshot

from app.infrastructure.repositories.in_memory import InMemoryPlanRunRepository
from app.planning.runner import run_planning


def test_in_memory_repository_stores_mvp_artifacts() -> None:
    request = PlanningSnapshot(
        planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
        planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
        employees=[
            EmployeeSnapshot(
                employee_id="e1",
                department_id="dep-1",
                availability=[
                    EmployeeAvailability(
                        start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                        end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
                    )
                ],
            )
        ],
        tasks=[
            TaskSnapshot(
                task_id="t1",
                department_id="dep-1",
                title="Task",
                starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
            )
        ],
    )
    response = run_planning(request)
    repository = InMemoryPlanRunRepository()

    repository.save(snapshot=request, response=response)

    stored_response = repository.get(response.summary.plan_run_id)
    records = repository.list_records()
    record = records[response.summary.plan_run_id]

    assert stored_response == response
    assert record.snapshot == request
    assert record.source_hash
    assert record.proposals == response.proposals
    assert record.unassigned == response.unassigned
    assert record.solver_statistics == response.artifacts.solver_statistics
