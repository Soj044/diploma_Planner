from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from contracts.schemas import (
    AssignmentProposal,
    CreatePlanRunRequest,
    PlanResponse,
    PlanRunArtifacts,
    PlanRunSummary,
    PlanningSnapshot,
)


def test_create_plan_run_request_rejects_invalid_period() -> None:
    with pytest.raises(ValidationError, match="planning_period_start must be before or equal"):
        CreatePlanRunRequest(
            planning_period_start=date(2026, 3, 24),
            planning_period_end=date(2026, 3, 23),
            initiated_by_user_id="manager-1",
        )


def test_assignment_proposal_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError, match="start_date must be before or equal"):
        AssignmentProposal(
            task_id="task-1",
            employee_id="emp-1",
            score=1.0,
            planned_hours=2,
            start_date=date(2026, 3, 24),
            end_date=date(2026, 3, 23),
        )


def test_planning_snapshot_rejects_task_outside_planning_period() -> None:
    with pytest.raises(ValidationError, match="all tasks must be inside the planning period"):
        PlanningSnapshot(
            planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
            planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
            employees=[],
            tasks=[
                {
                    "task_id": "task-1",
                    "title": "Outside period",
                    "starts_at": datetime(2026, 3, 22, 23, 0, tzinfo=timezone.utc),
                    "ends_at": datetime(2026, 3, 23, 1, 0, tzinfo=timezone.utc),
                }
            ],
        )


def test_plan_response_roundtrip_preserves_core_approval_fields() -> None:
    response = PlanResponse(
        summary=PlanRunSummary(
            plan_run_id="plan-1",
            status="completed",
            created_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
            planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
            planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
            assigned_count=1,
            unassigned_count=0,
        ),
        proposals=[
            AssignmentProposal(
                task_id="task-1",
                employee_id="emp-1",
                score=1.25,
                proposal_rank=1,
                is_selected=True,
                planned_hours=3,
                start_date=date(2026, 3, 23),
                end_date=date(2026, 3, 23),
                status="proposed",
            )
        ],
        unassigned=[],
        artifacts=PlanRunArtifacts(
            eligibility={"task-1": ["emp-1"]},
            scores={"task-1": {"emp-1": 1.25}},
            solver_statistics={"status": "OPTIMAL"},
        ),
    )

    roundtrip = PlanResponse.model_validate_json(response.model_dump_json())

    assert roundtrip.proposals[0].status == "proposed"
    assert roundtrip.proposals[0].is_selected is True
    assert roundtrip.proposals[0].planned_hours == 3
    assert roundtrip.proposals[0].start_date == date(2026, 3, 23)
    assert roundtrip.proposals[0].end_date == date(2026, 3, 23)
