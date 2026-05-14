"""SQLite repository for persisted planner artifacts.

This module saves plan runs, snapshots, proposals, and diagnostics between
planner-service restarts. It also exposes typed read helpers for internal AI
feeds and explanation context without introducing an ORM layer.
"""

from dataclasses import dataclass
import json
import sqlite3
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from contracts.schemas import (
    AssignmentProposal,
    CreatePlanRunRequest,
    PlanResponse,
    PlanRunArtifacts,
    PlanRunSummary,
    PlanningSnapshot,
    UnassignedTaskDiagnostic,
)

ALGORITHM_NAME = "cp_sat"
ALGORITHM_VERSION = "mvp-stage6"
OBJECTIVE_SUMMARY = "Maximize assigned tasks first, then prefer higher candidate scores."


@dataclass(frozen=True)
class PersistedPlanRunRecord:
    """One completed persisted plan run together with its saved snapshot and response."""

    internal_id: int
    plan_run_id: str
    initiated_by_user_id: str
    department_id: str | None
    status: str
    created_at: datetime
    snapshot: PlanningSnapshot
    response: PlanResponse


class SqlitePlanRunRepository:
    """Persist planner artifacts in a local SQLite file without introducing an ORM."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def save(
        self,
        command: CreatePlanRunRequest,
        snapshot: PlanningSnapshot,
        response: PlanResponse,
    ) -> None:
        """Persist the completed run and the MVP artifact slice in SQLite tables."""

        with self._connect() as connection:
            created_at = response.summary.created_at.isoformat()
            connection.execute(
                """
                INSERT INTO plan_runs (
                    external_uuid,
                    initiated_by_user_id,
                    department_id,
                    task_ids_json,
                    period_start,
                    period_end,
                    status,
                    algorithm_name,
                    algorithm_version,
                    objective_summary,
                    eligibility_json,
                    scores_json,
                    candidate_analysis_json,
                    time_estimates_json,
                    assigned_count,
                    unassigned_count,
                    created_at,
                    started_at,
                    finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_uuid) DO UPDATE SET
                    initiated_by_user_id = excluded.initiated_by_user_id,
                    department_id = excluded.department_id,
                    task_ids_json = excluded.task_ids_json,
                    period_start = excluded.period_start,
                    period_end = excluded.period_end,
                    status = excluded.status,
                    algorithm_name = excluded.algorithm_name,
                    algorithm_version = excluded.algorithm_version,
                    objective_summary = excluded.objective_summary,
                    eligibility_json = excluded.eligibility_json,
                    scores_json = excluded.scores_json,
                    candidate_analysis_json = excluded.candidate_analysis_json,
                    time_estimates_json = excluded.time_estimates_json,
                    assigned_count = excluded.assigned_count,
                    unassigned_count = excluded.unassigned_count,
                    created_at = excluded.created_at,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at
                """,
                (
                    response.summary.plan_run_id,
                    command.initiated_by_user_id,
                    command.department_id,
                    json.dumps(command.task_ids, sort_keys=True),
                    command.planning_period_start.isoformat(),
                    command.planning_period_end.isoformat(),
                    response.summary.status,
                    ALGORITHM_NAME,
                    ALGORITHM_VERSION,
                    OBJECTIVE_SUMMARY,
                    json.dumps(response.artifacts.eligibility, sort_keys=True),
                    json.dumps(response.artifacts.scores, sort_keys=True),
                    json.dumps(
                        {
                            task_id: [row.model_dump(mode="json") for row in rows]
                            for task_id, rows in response.artifacts.candidate_analysis.items()
                        },
                        sort_keys=True,
                    ),
                    json.dumps(
                        {
                            task_id: estimate.model_dump(mode="json")
                            for task_id, estimate in response.artifacts.time_estimates.items()
                        },
                        sort_keys=True,
                    ),
                    response.summary.assigned_count,
                    response.summary.unassigned_count,
                    created_at,
                    created_at,
                    created_at,
                ),
            )
            plan_run_row = connection.execute(
                "SELECT id FROM plan_runs WHERE external_uuid = ?",
                (response.summary.plan_run_id,),
            ).fetchone()
            plan_run_id = plan_run_row["id"]

            # Replace child artifacts atomically so a repeated save keeps a single source of truth per run.
            connection.execute("DELETE FROM plan_input_snapshots WHERE plan_run_id = ?", (plan_run_id,))
            connection.execute("DELETE FROM assignment_proposals WHERE plan_run_id = ?", (plan_run_id,))
            connection.execute("DELETE FROM unassigned_tasks WHERE plan_run_id = ?", (plan_run_id,))
            connection.execute("DELETE FROM solver_statistics WHERE plan_run_id = ?", (plan_run_id,))

            connection.execute(
                """
                INSERT INTO plan_input_snapshots (plan_run_id, source_hash, snapshot_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    plan_run_id,
                    self._source_hash(snapshot),
                    snapshot.model_dump_json(),
                    created_at,
                ),
            )
            connection.executemany(
                """
                INSERT INTO assignment_proposals (
                    plan_run_id,
                    external_task_id,
                    external_employee_id,
                    proposal_rank,
                    is_selected,
                    planned_hours,
                    start_date,
                    end_date,
                    score,
                    explanation_text,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        plan_run_id,
                        proposal.task_id,
                        proposal.employee_id,
                        proposal.proposal_rank,
                        int(proposal.is_selected),
                        proposal.planned_hours,
                        proposal.start_date.isoformat() if proposal.start_date else None,
                        proposal.end_date.isoformat() if proposal.end_date else None,
                        proposal.score,
                        proposal.explanation_text,
                        proposal.status,
                        created_at,
                    )
                    for proposal in response.proposals
                ],
            )
            connection.executemany(
                """
                INSERT INTO unassigned_tasks (
                    plan_run_id,
                    external_task_id,
                    reason_code,
                    message,
                    reason_details,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        plan_run_id,
                        item.task_id,
                        item.reason_code,
                        item.message,
                        item.reason_details,
                        created_at,
                    )
                    for item in response.unassigned
                ],
            )
            solver_stats = response.artifacts.solver_statistics
            connection.execute(
                """
                INSERT INTO solver_statistics (
                    plan_run_id,
                    solver_status,
                    objective_value,
                    wall_time_ms,
                    stats_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_run_id,
                    solver_stats.get("status", "UNKNOWN"),
                    solver_stats.get("objective_value"),
                    self._wall_time_ms(solver_stats),
                    json.dumps(solver_stats, sort_keys=True),
                    created_at,
                ),
            )

    def get(self, plan_run_id: str) -> PlanResponse | None:
        """Rebuild the public `PlanResponse` from persisted planner tables."""

        with self._connect() as connection:
            plan_run = self._get_plan_run_row(connection, plan_run_id)
            if plan_run is None:
                return None
            return self._load_persisted_record(connection, plan_run).response

    def get_record(self, plan_run_id: str) -> PersistedPlanRunRecord | None:
        """Return one typed persisted plan run record for internal AI read models."""

        with self._connect() as connection:
            plan_run = self._get_plan_run_row(connection, plan_run_id)
            if plan_run is None:
                return None
            return self._load_persisted_record(connection, plan_run)

    def list_completed_records(self, changed_since: datetime | None) -> list[PersistedPlanRunRecord]:
        """Return completed persisted plan runs filtered by the optional AI sync cursor."""

        query = """
            SELECT *
            FROM plan_runs
            WHERE status = 'completed'
        """
        parameters: tuple[object, ...] = ()
        if changed_since is not None:
            query += " AND created_at > ?"
            parameters = (changed_since.isoformat(),)
        query += " ORDER BY created_at, id"

        with self._connect() as connection:
            plan_runs = connection.execute(query, parameters).fetchall()
            return [self._load_persisted_record(connection, row) for row in plan_runs]

    def _connect(self) -> sqlite3.Connection:
        """Create a connection with row-based access and foreign keys enabled."""

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _get_plan_run_row(self, connection: sqlite3.Connection, plan_run_id: str) -> sqlite3.Row | None:
        """Load the raw `plan_runs` row for one external public plan run identifier."""

        return connection.execute(
            "SELECT * FROM plan_runs WHERE external_uuid = ?",
            (plan_run_id,),
        ).fetchone()

    def _load_persisted_record(
        self,
        connection: sqlite3.Connection,
        plan_run: sqlite3.Row,
    ) -> PersistedPlanRunRecord:
        """Rebuild one typed persisted plan run record from SQLite child tables."""

        snapshot_row = connection.execute(
            """
            SELECT snapshot_json
            FROM plan_input_snapshots
            WHERE plan_run_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (plan_run["id"],),
        ).fetchone()
        snapshot = PlanningSnapshot.model_validate_json(snapshot_row["snapshot_json"])

        proposals = [
            AssignmentProposal(
                task_id=row["external_task_id"],
                employee_id=row["external_employee_id"],
                score=row["score"],
                proposal_rank=row["proposal_rank"],
                is_selected=bool(row["is_selected"]),
                planned_hours=row["planned_hours"],
                start_date=datetime.fromisoformat(row["start_date"]).date() if row["start_date"] else None,
                end_date=datetime.fromisoformat(row["end_date"]).date() if row["end_date"] else None,
                status=row["status"],
                explanation_text=row["explanation_text"] or "",
            )
            for row in connection.execute(
                """
                SELECT *
                FROM assignment_proposals
                WHERE plan_run_id = ?
                ORDER BY proposal_rank, id
                """,
                (plan_run["id"],),
            ).fetchall()
        ]
        unassigned = [
            UnassignedTaskDiagnostic(
                task_id=row["external_task_id"],
                reason_code=row["reason_code"],
                message=row["message"],
                reason_details=row["reason_details"] or "",
            )
            for row in connection.execute(
                """
                SELECT *
                FROM unassigned_tasks
                WHERE plan_run_id = ?
                ORDER BY id
                """,
                (plan_run["id"],),
            ).fetchall()
        ]
        solver_row = connection.execute(
            "SELECT stats_json FROM solver_statistics WHERE plan_run_id = ?",
            (plan_run["id"],),
        ).fetchone()

        response = PlanResponse(
            summary=PlanRunSummary(
                plan_run_id=plan_run["external_uuid"],
                status=plan_run["status"],
                created_at=datetime.fromisoformat(plan_run["created_at"]),
                planning_period_start=snapshot.planning_period_start,
                planning_period_end=snapshot.planning_period_end,
                assigned_count=plan_run["assigned_count"],
                unassigned_count=plan_run["unassigned_count"],
            ),
            proposals=proposals,
            unassigned=unassigned,
            artifacts=PlanRunArtifacts(
                eligibility=json.loads(plan_run["eligibility_json"]),
                scores=json.loads(plan_run["scores_json"]),
                solver_statistics=json.loads(solver_row["stats_json"]) if solver_row else {},
                candidate_analysis=json.loads(plan_run["candidate_analysis_json"])
                if plan_run["candidate_analysis_json"]
                else {},
                time_estimates=json.loads(plan_run["time_estimates_json"])
                if plan_run["time_estimates_json"]
                else {},
            ),
        )
        return PersistedPlanRunRecord(
            internal_id=int(plan_run["id"]),
            plan_run_id=plan_run["external_uuid"],
            initiated_by_user_id=plan_run["initiated_by_user_id"],
            department_id=plan_run["department_id"],
            status=plan_run["status"],
            created_at=datetime.fromisoformat(plan_run["created_at"]),
            snapshot=snapshot,
            response=response,
        )

    def _ensure_schema(self) -> None:
        """Create the minimal Stage 6 planner tables if they do not exist yet."""

        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS plan_runs (
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
                    time_estimates_json TEXT NOT NULL DEFAULT '{}',
                    assigned_count INTEGER NOT NULL,
                    unassigned_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_plan_runs_status ON plan_runs(status);
                CREATE INDEX IF NOT EXISTS idx_plan_runs_period ON plan_runs(period_start, period_end);

                CREATE TABLE IF NOT EXISTS plan_input_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_run_id INTEGER NOT NULL REFERENCES plan_runs(id) ON DELETE CASCADE,
                    source_hash TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_plan_input_snapshots_plan_run_id ON plan_input_snapshots(plan_run_id);
                CREATE INDEX IF NOT EXISTS idx_plan_input_snapshots_source_hash ON plan_input_snapshots(source_hash);

                CREATE TABLE IF NOT EXISTS assignment_proposals (
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
                CREATE INDEX IF NOT EXISTS idx_assignment_proposals_plan_run_id ON assignment_proposals(plan_run_id);
                CREATE INDEX IF NOT EXISTS idx_assignment_proposals_task_id ON assignment_proposals(external_task_id);
                CREATE INDEX IF NOT EXISTS idx_assignment_proposals_employee_id ON assignment_proposals(external_employee_id);

                CREATE TABLE IF NOT EXISTS unassigned_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_run_id INTEGER NOT NULL REFERENCES plan_runs(id) ON DELETE CASCADE,
                    external_task_id TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    reason_details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_unassigned_tasks_plan_run_id ON unassigned_tasks(plan_run_id);
                CREATE INDEX IF NOT EXISTS idx_unassigned_tasks_task_id ON unassigned_tasks(external_task_id);

                CREATE TABLE IF NOT EXISTS solver_statistics (
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
            self._ensure_plan_runs_column(
                connection,
                column_name="candidate_analysis_json",
                column_definition="TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_plan_runs_column(
                connection,
                column_name="time_estimates_json",
                column_definition="TEXT NOT NULL DEFAULT '{}'",
            )

    def _source_hash(self, snapshot: PlanningSnapshot) -> str:
        """Hash the snapshot payload so the persisted run can be reproduced and compared."""

        return sha256(snapshot.model_dump_json().encode("utf-8")).hexdigest()

    def _wall_time_ms(self, solver_stats: dict[str, int | float | str]) -> int | None:
        """Convert the solver wall time to milliseconds for storage in the statistics table."""

        wall_time_seconds = solver_stats.get("wall_time_sec")
        if wall_time_seconds is None:
            return None
        return int(float(wall_time_seconds) * 1000)

    def _ensure_plan_runs_column(
        self,
        connection: sqlite3.Connection,
        *,
        column_name: str,
        column_definition: str,
    ) -> None:
        """Add one missing `plan_runs` column for backward-compatible local upgrades."""

        rows = connection.execute("PRAGMA table_info(plan_runs)").fetchall()
        existing_columns = {row["name"] for row in rows}
        if column_name in existing_columns:
            return
        connection.execute(f"ALTER TABLE plan_runs ADD COLUMN {column_name} {column_definition}")
