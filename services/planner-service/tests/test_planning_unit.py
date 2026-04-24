from datetime import datetime, timezone

from contracts.schemas import EmployeeAvailability, EmployeeSnapshot, SkillRequirement, TaskSnapshot

from app.planning.eligibility import evaluate_eligibility
from app.planning.scoring import calculate_scores


def test_eligibility_filters_by_department_availability_and_skill() -> None:
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


def test_scoring_returns_positive_ratio() -> None:
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
