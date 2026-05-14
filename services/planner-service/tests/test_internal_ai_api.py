"""Unit tests for planner-service internal AI helper routes."""

from datetime import date, datetime, timezone

from fastapi import HTTPException
import pytest

from contracts.schemas import (
    CreatePlanRunRequest,
    EmployeeAvailability,
    EmployeeSnapshot,
    PlanningSnapshot,
    TaskSnapshot,
)

from app.api import internal_ai
from app.infrastructure.repositories.sqlite import SqlitePlanRunRepository
from app.planning.runner import run_planning


def _build_command() -> CreatePlanRunRequest:
    """Build one persisted planner command reused by internal AI tests."""

    return CreatePlanRunRequest(
        planning_period_start=date(2026, 3, 23),
        planning_period_end=date(2026, 3, 23),
        initiated_by_user_id="manager-1",
        department_id="dep-1",
        task_ids=["task-1", "task-2"],
    )


def _build_snapshot() -> PlanningSnapshot:
    """Build one snapshot that produces both a proposal and an unassigned diagnostic."""

    return PlanningSnapshot(
        planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
        planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
        employees=[
            EmployeeSnapshot(
                employee_id="emp-1",
                department_id="dep-1",
                skill_levels={"skill-assembly": 4},
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
                ends_at=datetime(2026, 3, 23, 13, 0, tzinfo=timezone.utc),
                estimated_hours=4,
            ),
            TaskSnapshot(
                task_id="task-2",
                department_id="dep-1",
                title="Overflow task",
                starts_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 17, 0, tzinfo=timezone.utc),
                estimated_hours=5,
            ),
        ],
    )


@pytest.fixture()
def persisted_run_repository(tmp_path, monkeypatch) -> tuple[SqlitePlanRunRepository, object]:
    """Persist one completed run and swap the internal AI module to that repository."""

    repository = SqlitePlanRunRepository(db_path=tmp_path / "planner-ai.sqlite3")
    snapshot = _build_snapshot()
    response = run_planning(snapshot)
    repository.save(command=_build_command(), snapshot=snapshot, response=response)
    monkeypatch.setattr(internal_ai, "repository", repository)
    monkeypatch.setattr(internal_ai, "INTERNAL_SERVICE_TOKEN", "shared-ai-token")
    return repository, response


def test_require_internal_ai_access_requires_token(monkeypatch) -> None:
    """Reject internal AI access when the shared token header is missing."""

    monkeypatch.setattr(internal_ai, "INTERNAL_SERVICE_TOKEN", "shared-ai-token")

    with pytest.raises(HTTPException) as exc_info:
        internal_ai.require_internal_ai_access(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Internal service token is required."


def test_require_internal_ai_access_rejects_invalid_token(monkeypatch) -> None:
    """Reject internal AI access when the shared token does not match."""

    monkeypatch.setattr(internal_ai, "INTERNAL_SERVICE_TOKEN", "shared-ai-token")

    with pytest.raises(HTTPException) as exc_info:
        internal_ai.require_internal_ai_access("wrong-token")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Internal service token is invalid."


def test_internal_ai_service_boundary_returns_planner_ownership(monkeypatch) -> None:
    """Return the planner truth boundary for trusted internal AI callers."""

    monkeypatch.setattr(internal_ai, "INTERNAL_SERVICE_TOKEN", "shared-ai-token")
    internal_ai.require_internal_ai_access("shared-ai-token")

    payload = internal_ai.get_internal_ai_service_boundary()

    assert payload["service"] == "planner-service"
    assert payload["responsibility"] == "proposals and diagnostics truth"


def test_internal_ai_index_feed_returns_unassigned_case(
    persisted_run_repository: tuple[SqlitePlanRunRepository, object],
) -> None:
    """Return flattened `unassigned_case` items for completed persisted plan runs."""

    _repository, response = persisted_run_repository
    payload = internal_ai.get_internal_ai_index_feed(changed_since=None)
    diagnostic = response.unassigned[0]

    assert payload["source_service"] == "planner-service"
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["source_type"] == "unassigned_case"
    assert item["source_key"] == f"unassigned:{response.summary.plan_run_id}:{diagnostic.task_id}"
    assert item["metadata"]["reason_code"] == diagnostic.reason_code
    assert item["metadata"]["time_estimate"]["source"] == "manual"
    assert "eligible_conflict_count" in item["metadata"]


def test_internal_ai_index_feed_filters_by_changed_since(
    persisted_run_repository: tuple[SqlitePlanRunRepository, object],
) -> None:
    """Skip completed plan runs that are not newer than the incremental sync cursor."""

    _repository, response = persisted_run_repository
    future_cursor = (response.summary.created_at.replace(tzinfo=timezone.utc)).isoformat()
    payload = internal_ai.get_internal_ai_index_feed(changed_since=future_cursor)

    assert payload["items"] == []


def test_internal_ai_proposal_context_returns_persisted_task_slice(
    persisted_run_repository: tuple[SqlitePlanRunRepository, object],
) -> None:
    """Return one persisted proposal context with sibling proposals and score data."""

    _repository, response = persisted_run_repository
    proposal = response.proposals[0]

    payload = internal_ai.get_internal_ai_proposal_context(
        plan_run_id=response.summary.plan_run_id,
        task_id=proposal.task_id,
        employee_id=proposal.employee_id,
    )

    assert payload["proposal"]["employee_id"] == proposal.employee_id
    assert payload["task_snapshot"]["task_id"] == proposal.task_id
    assert payload["eligibility"]["eligible_count"] == 1
    assert payload["score_map"][proposal.employee_id] == response.artifacts.scores[proposal.task_id][proposal.employee_id]
    assert payload["candidate_analysis"][0]["outcome_code"] == "selected"
    assert payload["selected_employee_id"] == proposal.employee_id
    assert payload["task_snapshot"]["priority"] == "medium"
    assert payload["time_estimate"]["source"] == "manual"


def test_internal_ai_unassigned_context_returns_persisted_diagnostic_slice(
    persisted_run_repository: tuple[SqlitePlanRunRepository, object],
) -> None:
    """Return one persisted unassigned-task context with diagnostics and solver data."""

    _repository, response = persisted_run_repository
    diagnostic = response.unassigned[0]

    payload = internal_ai.get_internal_ai_unassigned_context(
        plan_run_id=response.summary.plan_run_id,
        task_id=diagnostic.task_id,
    )

    assert payload["diagnostic"]["task_id"] == diagnostic.task_id
    assert payload["diagnostic"]["reason_code"] == diagnostic.reason_code
    assert payload["task_snapshot"]["task_id"] == diagnostic.task_id
    assert payload["solver_summary"]["status"] == response.artifacts.solver_statistics["status"]
    assert payload["candidate_analysis"][0]["outcome_code"] == "eligible_not_selected_capacity_or_conflict"
    assert payload["time_estimate"]["effective_hours"] == response.artifacts.time_estimates[
        diagnostic.task_id
    ].effective_hours
