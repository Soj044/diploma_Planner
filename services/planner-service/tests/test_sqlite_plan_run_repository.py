import sqlite3
from datetime import date, datetime, timezone

from contracts.schemas import CreatePlanRunRequest, EmployeeAvailability, EmployeeSnapshot, PlanningSnapshot, TaskSnapshot

from app.infrastructure.repositories.sqlite import SqlitePlanRunRepository
from app.planning.runner import run_planning


def build_command() -> CreatePlanRunRequest:
    return CreatePlanRunRequest(
        planning_period_start=date(2026, 3, 23),
        planning_period_end=date(2026, 3, 23),
        initiated_by_user_id="manager-1",
        department_id="dep-1",
        task_ids=["task-1"],
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
                        end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
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


def test_sqlite_repository_persists_run_across_repository_instances(tmp_path) -> None:
    db_path = tmp_path / "planner.sqlite3"
    repository = SqlitePlanRunRepository(db_path=db_path)
    command = build_command()
    snapshot = build_snapshot()
    response = run_planning(snapshot)

    repository.save(command=command, snapshot=snapshot, response=response)

    reloaded_repository = SqlitePlanRunRepository(db_path=db_path)
    loaded_response = reloaded_repository.get(response.summary.plan_run_id)

    assert db_path.exists()
    assert loaded_response == response

    with sqlite3.connect(db_path) as connection:
        plan_runs_count = connection.execute("SELECT COUNT(*) FROM plan_runs").fetchone()[0]
        snapshots_count = connection.execute("SELECT COUNT(*) FROM plan_input_snapshots").fetchone()[0]
        proposals_count = connection.execute("SELECT COUNT(*) FROM assignment_proposals").fetchone()[0]
        unassigned_count = connection.execute("SELECT COUNT(*) FROM unassigned_tasks").fetchone()[0]
        solver_stats_count = connection.execute("SELECT COUNT(*) FROM solver_statistics").fetchone()[0]

    assert plan_runs_count == 1
    assert snapshots_count == 1
    assert proposals_count == 1
    assert unassigned_count == 0
    assert solver_stats_count == 1
