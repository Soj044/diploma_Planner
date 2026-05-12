from datetime import datetime, timezone

import pytest

from contracts.schemas import (
    EmployeeAvailability,
    EmployeeSnapshot,
    HistoricalTaskSummary,
    SkillRequirement,
    TaskSnapshot,
)

from app.planning.eligibility import evaluate_eligibility
from app.planning.scoring import calculate_scores
from app.planning.time_estimation import build_task_effort_map


def _task_effort_map(
    tasks: list[TaskSnapshot],
    historical_tasks: list[HistoricalTaskSummary] | None = None,
):
    return build_task_effort_map(tasks, historical_tasks or [])


def test_eligibility_filters_by_department_availability_and_skill() -> None:
    """Keep department and required-skill filters intact for otherwise eligible employees."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
        estimated_hours=1,
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

    eligibility = evaluate_eligibility(employees, [task], _task_effort_map([task]))
    assert eligibility.by_task["t1"] == ["e-ok"]
    trace_by_employee = {
        trace.employee_id: trace
        for trace in eligibility.traces_by_task["t1"]
    }
    assert trace_by_employee["e-wrong-dep"].matched_department is False


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

    eligibility = evaluate_eligibility(employees, [task], _task_effort_map([task]))

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

    eligibility = evaluate_eligibility(employees, [task], _task_effort_map([task]))

    assert eligibility.by_task["t1"] == []
    assert eligibility.traces_by_task["t1"][0].available_hours_in_window == 3


def test_eligibility_traces_missing_skills_for_candidate_analysis() -> None:
    """Record missing required skill ids so AI explanations can reuse hard-filter facts."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 13, 0, tzinfo=timezone.utc),
        estimated_hours=4,
        requirements=[SkillRequirement(skill_id="skill-a", min_level=3)],
    )
    employee = EmployeeSnapshot(
        employee_id="e-missing-skill",
        department_id="dep-1",
        skill_levels={"skill-a": 1},
        availability=[
            EmployeeAvailability(
                start_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 23, 17, 0, tzinfo=timezone.utc),
                available_hours=8,
            )
        ],
    )

    eligibility = evaluate_eligibility([employee], [task], _task_effort_map([task]))

    assert eligibility.by_task["t1"] == []
    assert eligibility.traces_by_task["t1"][0].missing_skill_ids == ["skill-a"]


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

    eligibility = evaluate_eligibility([employee], [task], _task_effort_map([task]))

    assert eligibility.by_task["t1"] == ["e-derived-hours"]


def test_scoring_returns_positive_ratio() -> None:
    """Keep score calculation positive for eligible candidates after availability changes."""

    task = TaskSnapshot(
        task_id="t1",
        department_id="dep-1",
        title="Task",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 10, 0, tzinfo=timezone.utc),
        estimated_hours=1,
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

    eligibility = evaluate_eligibility([employee], [task], _task_effort_map([task]))
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
        estimated_hours=1,
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

    eligibility = evaluate_eligibility([employee], [task], _task_effort_map([task]))
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
        estimated_hours=1,
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

    eligibility = evaluate_eligibility([employee], [task], _task_effort_map([task]))
    scores = calculate_scores([employee], [task], eligibility)

    assert scores.by_task["t1"]["e1"] == 1.0


def test_time_estimation_keeps_manual_estimate_when_present() -> None:
    task = TaskSnapshot(
        task_id="t-manual",
        department_id="dep-1",
        title="Manual estimate task",
        priority="high",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 17, 0, tzinfo=timezone.utc),
        estimated_hours=6,
        requirements=[SkillRequirement(skill_id="skill-a", min_level=2, weight=1.5)],
    )

    effort = build_task_effort_map([task], [])["t-manual"]

    assert effort.source == "manual"
    assert effort.effective_hours == 6
    assert effort.manual_hours == 6
    assert effort.rules_baseline_hours == 7


def test_time_estimation_uses_history_when_multiple_matches_exist() -> None:
    task = TaskSnapshot(
        task_id="t-history",
        department_id="dep-1",
        title="History estimate task",
        priority="medium",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 17, 0, tzinfo=timezone.utc),
        requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
    )
    history = [
        HistoricalTaskSummary(
            task_id="h1",
            department_id="dep-1",
            priority="medium",
            estimated_hours=4,
            actual_hours=5,
            requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
            due_date=datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc).date(),
        ),
        HistoricalTaskSummary(
            task_id="h2",
            department_id="dep-1",
            priority="medium",
            estimated_hours=4,
            actual_hours=6,
            requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
            due_date=datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc).date(),
        ),
        HistoricalTaskSummary(
            task_id="h3",
            department_id="dep-1",
            priority="medium",
            estimated_hours=4,
            actual_hours=7,
            requirements=[SkillRequirement(skill_id="skill-a", min_level=2)],
            due_date=datetime(2026, 3, 18, 0, 0, tzinfo=timezone.utc).date(),
        ),
    ]

    effort = build_task_effort_map([task], history)["t-history"]

    assert effort.source == "history"
    assert effort.effective_hours == 6
    assert effort.historical_median_hours == pytest.approx(6.0)
    assert effort.historical_sample_size == 3


def test_time_estimation_blends_rules_with_small_history_sample() -> None:
    task = TaskSnapshot(
        task_id="t-blended",
        department_id="dep-1",
        title="Blended estimate task",
        priority="medium",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 17, 0, tzinfo=timezone.utc),
    )
    history = [
        HistoricalTaskSummary(
            task_id="h1",
            department_id="dep-1",
            priority="medium",
            estimated_hours=8,
            actual_hours=10,
            requirements=[],
            due_date=datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc).date(),
        ),
        HistoricalTaskSummary(
            task_id="h2",
            department_id="dep-1",
            priority="medium",
            estimated_hours=8,
            actual_hours=14,
            requirements=[],
            due_date=datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc).date(),
        ),
    ]

    effort = build_task_effort_map([task], history)["t-blended"]

    assert effort.source == "blended"
    assert effort.rules_baseline_hours == 8
    assert effort.historical_median_hours == pytest.approx(12.0)
    assert effort.effective_hours == 10


def test_time_estimation_falls_back_to_rules_without_matches() -> None:
    task = TaskSnapshot(
        task_id="t-rules",
        department_id="dep-1",
        title="Rules estimate task",
        priority="critical",
        starts_at=datetime(2026, 3, 23, 9, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 3, 23, 17, 0, tzinfo=timezone.utc),
        requirements=[SkillRequirement(skill_id="skill-a", min_level=2, weight=1.5)],
    )
    unmatched_history = [
        HistoricalTaskSummary(
            task_id="h1",
            department_id="dep-2",
            priority="low",
            estimated_hours=2,
            actual_hours=3,
            requirements=[SkillRequirement(skill_id="skill-b", min_level=1)],
            due_date=datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc).date(),
        )
    ]

    effort = build_task_effort_map([task], unmatched_history)["t-rules"]

    assert effort.source == "rules"
    assert effort.effective_hours == 8
    assert effort.historical_sample_size == 0
