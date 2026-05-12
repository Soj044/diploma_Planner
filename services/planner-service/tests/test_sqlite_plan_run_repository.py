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


def test_sqlite_repository_roundtrip_preserves_full_artifact_slice(tmp_path) -> None:
    db_path = tmp_path / "planner.sqlite3"
    repository = SqlitePlanRunRepository(db_path=db_path)
    command = build_command()
    snapshot = PlanningSnapshot(
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
                title="Primary task",
                starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
                estimated_hours=3,
            ),
            TaskSnapshot(
                task_id="task-2",
                department_id="dep-1",
                title="Overlapping task",
                starts_at=datetime(2026, 3, 23, 11, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 13, 0, tzinfo=timezone.utc),
                estimated_hours=2,
            ),
        ],
    )
    response = run_planning(snapshot)

    repository.save(command=command, snapshot=snapshot, response=response)
    loaded_response = repository.get(response.summary.plan_run_id)

    assert loaded_response is not None
    assert loaded_response == response
    assert loaded_response.summary.assigned_count == 1
    assert loaded_response.summary.unassigned_count == 1
    assert loaded_response.proposals[0].status == "proposed"
    assert loaded_response.proposals[0].is_selected is True
    assert loaded_response.proposals[0].task_id in {"task-1", "task-2"}
    if loaded_response.proposals[0].task_id == "task-1":
        assert loaded_response.proposals[0].planned_hours == 3
    else:
        assert loaded_response.proposals[0].planned_hours == 2
    assert loaded_response.unassigned[0].reason_code == "capacity_or_conflict"
    assert loaded_response.artifacts.eligibility
    assert loaded_response.artifacts.scores
    assert loaded_response.artifacts.solver_statistics
    assert loaded_response.artifacts.candidate_analysis
    assert loaded_response.artifacts.time_estimates
    assert loaded_response.artifacts.time_estimates["task-1"].source == "manual"
    assert loaded_response.artifacts.time_estimates["task-2"].source == "manual"


def test_sqlite_repository_upgrades_existing_plan_runs_without_time_estimates_column(tmp_path) -> None:
    db_path = tmp_path / "planner-legacy.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE plan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_uuid TEXT NOT NULL UNIQUE,
                initiated_by_user_id TEXT NOT NULL,
                department_id TEXT,
                task_ids_json TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                status TEXT NOT NULL,
                algorithm_name TEXT NOT NULL,
                algorithm_version TEXT NOT NULL,
                objective_summary TEXT,
                eligibility_json TEXT NOT NULL,
                scores_json TEXT NOT NULL,
                candidate_analysis_json TEXT NOT NULL DEFAULT '{}',
                assigned_count INTEGER NOT NULL,
                unassigned_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            );
            CREATE TABLE plan_input_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_run_id INTEGER NOT NULL REFERENCES plan_runs(id) ON DELETE CASCADE,
                source_hash TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE assignment_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_run_id INTEGER NOT NULL REFERENCES plan_runs(id) ON DELETE CASCADE,
                external_task_id TEXT NOT NULL,
                external_employee_id TEXT NOT NULL,
                proposal_rank INTEGER NOT NULL,
                is_selected INTEGER NOT NULL,
                planned_hours INTEGER,
                start_date TEXT,
                end_date TEXT,
                score REAL NOT NULL,
                explanation_text TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE unassigned_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_run_id INTEGER NOT NULL REFERENCES plan_runs(id) ON DELETE CASCADE,
                external_task_id TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                message TEXT NOT NULL,
                reason_details TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE solver_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_run_id INTEGER NOT NULL UNIQUE REFERENCES plan_runs(id) ON DELETE CASCADE,
                solver_status TEXT NOT NULL,
                objective_value REAL,
                wall_time_ms INTEGER,
                stats_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

    repository = SqlitePlanRunRepository(db_path=db_path)
    command = build_command()
    snapshot = build_snapshot()
    response = run_planning(snapshot)

    repository.save(command=command, snapshot=snapshot, response=response)
    loaded_response = repository.get(response.summary.plan_run_id)

    assert loaded_response is not None
    assert loaded_response.artifacts.time_estimates["task-1"].effective_hours == 3
