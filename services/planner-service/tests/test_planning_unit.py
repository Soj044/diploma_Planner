from datetime import datetime, timezone

import pytest

from contracts.schemas import EmployeeAvailability, EmployeeSnapshot, SkillRequirement, TaskSnapshot

from app.planning.eligibility import evaluate_eligibility
from app.planning.scoring import calculate_scores


def test_eligibility_filters_by_department_availability_and_skill() -> None:
    """Keep department and required-skill filters intact for otherwise eligible employees."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
        requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
    )

    employees = [
        EmployeeSnapshot(
            employee_id="e-ok",
            department_id="dep-1",
            is_active=True,
            skill_levels={"skill-a": 2},
            availability=[
                EmployeeAvailability(
                    start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                    end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
                )
            ],
        ),
        EmployeeSnapshot(
            employee_id="e-wrong-dep",
            department_id="dep-2",
            is_active=True,
            skill_levels={"skill-a": 3},
            availability=[
                EmployeeAvailability(
                    start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                    end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
                )
            ],
        ),
    ]

    eligibility = evaluate_eligibility(employees, [task])
    assert eligibility.by_task["t1"] == ["e-ok"]


def test_eligibility_allows_cumulative_multi_slot_availability_within_task_window() -> None:
    """Accept multi-day tasks when intersecting slots provide enough total hours."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Task",
        starts_at=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 5, 16, 0, 0, tzinfo=timezone.utc),
        estimated_hours=8,
    )

    employees = [
        EmployeeSnapshot(
            employee_id="e-multi-day",
            department_id="dep-1",
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
    ]

    eligibility = evaluate_eligibility(employees, [task])

    assert eligibility.by_task["t1"] == ["e-multi-day"]


def test_eligibility_rejects_employee_with_insufficient_total_availability_hours() -> None:
    """Reject employees when intersecting slots do not reach the task hour requirement."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 13, 0, tzinfo=timezone.utc),
        estimated_hours=4,
    )
    employees = [
        EmployeeSnapshot(
            employee_id="e-insufficient-hours",
            department_id="dep-1",
            availability=[
                EmployeeAvailability(
                    start_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                    end_at=datetime(2026, 3, 23, 11, 0, tzinfo=timezone.utc),
                    available_hours=2,
                ),
                EmployeeAvailability(
                    start_at=datetime(2026, 3, 23, 11, 0, tzinfo=timezone.utc),
                    end_at=datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
                    available_hours=1,
                ),
            ],
        )
    ]

    eligibility = evaluate_eligibility(employees, [task])

    assert eligibility.by_task["t1"] == []


def test_eligibility_uses_overlap_duration_when_slot_hours_are_missing() -> None:
    """Fall back to overlap duration when the snapshot omits explicit available hours."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 13, 0, tzinfo=timezone.utc),
        estimated_hours=4,
    )
    employee = EmployeeSnapshot(
        employee_id="e-derived-hours",
        department_id="dep-1",
        availability=[
            EmployeeAvailability(
                start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 23, 11, 0, tzinfo=timezone.utc),
            ),
            EmployeeAvailability(
                start_at=datetime(2026, 3, 23, 11, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 23, 14, 0, tzinfo=timezone.utc),
            ),
        ],
    )

    eligibility = evaluate_eligibility([employee], [task])

    assert eligibility.by_task["t1"] == ["e-derived-hours"]


def test_scoring_returns_positive_ratio() -> None:
    """Keep score calculation positive for eligible candidates after availability changes."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
        requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
    )
    employee = EmployeeSnapshot(
        employee_id="e1",
        department_id="dep-1",
        skill_levels={"skill-a": 4},
        availability=[
            EmployeeAvailability(
                start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
            )
        ],
    )

    eligibility = evaluate_eligibility([employee], [task])
    scores = calculate_scores([employee], [task], eligibility)
    assert scores.by_task["t1"]["e1"] >= 1.0


def test_scoring_uses_requirement_weights_and_caps_skill_bonus() -> None:
    """Preserve weighted skill scoring after the availability rule change."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Weighted task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
        requirements=[
            SkillRequirement(skill_id="skill-a", min_level=2, weight=1.0),
            SkillRequirement(skill_id="skill-b", min_level=1, weight=3.0),
        ],
    )
    employee = EmployeeSnapshot(
        employee_id="e1",
        department_id="dep-1",
        skill_levels={"skill-a": 10, "skill-b": 1},
        availability=[
            EmployeeAvailability(
                start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
            )
        ],
    )

    eligibility = evaluate_eligibility([employee], [task])
    scores = calculate_scores([employee], [task], eligibility)

    assert scores.by_task["t1"]["e1"] == pytest.approx(1.25)


def test_scoring_defaults_to_one_without_requirements() -> None:
    """Preserve the neutral score for requirement-free tasks."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Unspecified skill task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
    )
    employee = EmployeeSnapshot(
        employee_id="e1",
        department_id="dep-1",
        availability=[
            EmployeeAvailability(
                start_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
            )
        ],
    )

    eligibility = evaluate_eligibility([employee], [task])
    scores = calculate_scores([employee], [task], eligibility)

    assert scores.by_task["t1"]["e1"] == 1.0
