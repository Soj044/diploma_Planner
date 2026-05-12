from datetime import datetime, timezone

from contracts.schemas import (
    EmployeeAvailability,
    EmployeeSnapshot,
    PlanningSnapshot,
    SkillRequirement,
    TaskSnapshot,
)

from app.planning.runner import run_planning


def test_snapshot_to_proposals_and_unassigned_diagnostics() -> None:
    """Keep the baseline happy-path and no-eligible diagnostic flow intact."""

    request = PlanningSnapshot(
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


def test_date_based_multi_day_task_can_use_cumulative_daily_availability() -> None:
    """Allow planner proposals when daily slots add up to the required task hours."""

    snapshot = PlanningSnapshot(
        planning_period_start=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
        planning_period_end=datetime(2026, 5, 16, 0, 0, tzinfo=timezone.utc),
        employees=[
            EmployeeSnapshot(
                employee_id="e1",
                department_id="dep-1",
                skill_levels={"skill-a": 3},
                availability=[
                    EmployeeAvailability(
                        start_at=datetime(2026, 5, 13, 9, 0, tzinfo=timezone.utc),
                        end_at=datetime(2026, 5, 13, 18, 0, tzinfo=timezone.utc),
                        available_hours=8,
                    ),
                    EmployeeAvailability(
                        start_at=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
                        end_at=datetime(2026, 5, 14, 18, 0, tzinfo=timezone.utc),
                        available_hours=8,
                    ),
                    EmployeeAvailability(
                        start_at=datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc),
                        end_at=datetime(2026, 5, 15, 18, 0, tzinfo=timezone.utc),
                        available_hours=8,
                    ),
                ],
            )
        ],
        tasks=[
            TaskSnapshot(
                task_id="t-multi-day",
                department_id="dep-1",
                title="Date based multi-day task",
                starts_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 5, 16, 0, 0, tzinfo=timezone.utc),
                estimated_hours=8,
                requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
            )
        ],
    )

    response = run_planning(snapshot)

    assert response.summary.assigned_count == 1
    assert response.summary.unassigned_count == 0
    assert response.proposals[0].task_id == "t-multi-day"
    assert response.proposals[0].employee_id == "e1"


def test_optimizer_leaves_overlapping_task_as_capacity_conflict() -> None:
    """Keep optimizer conflict diagnostics stable after eligibility changes."""

    snapshot = PlanningSnapshot(
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
                        available_hours=8,
                    )
                ],
            )
        ],
        tasks=[
            TaskSnapshot(
                task_id="t-first",
                department_id="dep-1",
                title="First task",
                starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
                estimated_hours=3,
            ),
            TaskSnapshot(
                task_id="t-overlap",
                department_id="dep-1",
                title="Overlapping task",
                starts_at=datetime(2026, 3, 23, 11, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 13, 0, tzinfo=timezone.utc),
                estimated_hours=2,
            ),
        ],
    )

    response = run_planning(snapshot)

    assert response.summary.assigned_count == 1
    assert response.summary.unassigned_count == 1
    assert len(response.proposals) == 1
    assert response.unassigned[0].reason_code == "capacity_or_conflict"
    assert response.unassigned[0].task_id in {"t-first", "t-overlap"}


def test_optimizer_keeps_inclusive_end_date_for_date_based_tasks() -> None:
    """Preserve the inclusive due-date mapping for date-only task assignments."""

    snapshot = PlanningSnapshot(
        planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
        planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
        employees=[
            EmployeeSnapshot(
                employee_id="e1",
                department_id="dep-1",
                availability=[
                    EmployeeAvailability(
                        start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                        end_at=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
                        available_hours=8,
                    )
                ],
            )
        ],
        tasks=[
            TaskSnapshot(
                task_id="t-date-based",
                department_id="dep-1",
                title="Date based task",
                starts_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
                estimated_hours=4,
            )
        ],
    )

    response = run_planning(snapshot)

    assert response.summary.assigned_count == 1
    assert len(response.proposals) == 1
    assert response.proposals[0].start_date.isoformat() == "2026-03-23"
    assert response.proposals[0].end_date.isoformat() == "2026-03-23"


def test_candidate_analysis_marks_lower_score_outcome_for_unselected_eligible_candidate() -> None:
    """Persist a lower-score comparison fact when one task has multiple eligible candidates."""

    snapshot = PlanningSnapshot(
        planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
        planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
        employees=[
            EmployeeSnapshot(
                employee_id="e-top",
                department_id="dep-1",
                skill_levels={"skill-a": 4},
                availability=[
                    EmployeeAvailability(
                        start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                        end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
                        available_hours=8,
                    )
                ],
            ),
            EmployeeSnapshot(
                employee_id="e-alt",
                department_id="dep-1",
                skill_levels={"skill-a": 3},
                availability=[
                    EmployeeAvailability(
                        start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                        end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
                        available_hours=8,
                    )
                ],
            ),
        ],
            tasks=[
                TaskSnapshot(
                    task_id="t-primary",
                    department_id="dep-1",
                    title="Primary task",
                    starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                    ends_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
                    estimated_hours=3,
                    requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
                )
            ],
        )

    response = run_planning(snapshot)

    primary_analysis = response.artifacts.candidate_analysis["t-primary"]
    assert any(row.outcome_code == "selected" for row in primary_analysis)
    assert any(row.outcome_code == "eligible_not_selected_lower_score" for row in primary_analysis)


def test_candidate_analysis_marks_capacity_conflict_for_unassigned_task() -> None:
    """Persist a conflict-driven comparison fact when eligible candidates remain unassigned."""

    snapshot = PlanningSnapshot(
        planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
        planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
        employees=[
            EmployeeSnapshot(
                employee_id="e-top",
                department_id="dep-1",
                skill_levels={"skill-a": 4},
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
                task_id="t-first",
                department_id="dep-1",
                title="First task",
                starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
                estimated_hours=3,
                requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
            ),
            TaskSnapshot(
                task_id="t-overlap",
                department_id="dep-1",
                title="Overlap task",
                starts_at=datetime(2026, 3, 23, 11, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 3, 23, 14, 0, tzinfo=timezone.utc),
                estimated_hours=3,
                requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
            ),
        ],
    )

    response = run_planning(snapshot)
    unassigned_task_id = response.unassigned[0].task_id
    conflict_analysis = response.artifacts.candidate_analysis[unassigned_task_id]

    assert any(row.outcome_code == "eligible_not_selected_capacity_or_conflict" for row in conflict_analysis)
