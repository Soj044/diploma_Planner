from datetime import datetime, timezone

from contracts.schemas import (
    EmployeeAvailability,
    EmployeeSnapshot,
    PlanRequest,
    SkillRequirement,
    TaskSnapshot,
)

from app.planning.runner import run_planning


def test_snapshot_to_proposals_and_unassigned_diagnostics() -> None:
    request = PlanRequest(
        planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
        planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
        employees=[
            EmployeeSnapshot(
                employee_id="e1",
                department_id="dep-1",
                skill_levels={"skill-a": 2},
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
                task_id="t-ok",
                department_id="dep-1",
                title="Task ok",
                starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
                requirements=[SkillRequirement(skill_id="skill-a", min_level=1)],
            ),
            TaskSnapshot(
                task_id="t-no-eligible",
                department_id="dep-1",
                title="Task no eligible",
                starts_at=datetime(2026, 3, 23, 11, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
                requirements=[SkillRequirement(skill_id="skill-b", min_level=1)],
            ),
        ],
    )

    response = run_planning(request)

    assert response.summary.assigned_count == 1
    assert response.summary.status == "completed"
    assert response.summary.planning_period_start == request.planning_period_start
    assert len(response.proposals) == 1
    assert response.proposals[0].task_id == "t-ok"
    assert response.proposals[0].planned_hours == 1
    assert response.proposals[0].status == "proposed"

    assert response.summary.unassigned_count == 1
    assert response.unassigned[0].task_id == "t-no-eligible"
    assert response.unassigned[0].reason_code == "no_eligible_candidates"
