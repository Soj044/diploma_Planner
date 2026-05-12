"""Planner-side effort estimation that combines manual input, rules, and history.

The planner must use one consistent task-effort map across eligibility,
optimization, diagnostics, and persisted review artifacts so managers can see
where planned hours came from.
"""

from __future__ import annotations

from datetime import timedelta
from math import ceil, floor
from statistics import median

from contracts.schemas import HistoricalTaskSummary, TaskSnapshot, TaskTimeEstimate

TaskEffortMap = dict[str, TaskTimeEstimate]

PRIORITY_MULTIPLIERS = {
    "low": 0.9,
    "medium": 1.0,
    "high": 1.15,
    "critical": 1.3,
}


def build_task_effort_map(
    tasks: list[TaskSnapshot],
    historical_tasks: list[HistoricalTaskSummary],
) -> TaskEffortMap:
    """Estimate the effective effort for every live planning task."""

    return {
        task.task_id: _estimate_task_effort(task=task, historical_tasks=historical_tasks)
        for task in tasks
    }


def effective_task_hours(task_id: str, task_effort_map: TaskEffortMap) -> int:
    """Return the planner-wide effective hours that must be reused for one task."""

    estimate = task_effort_map.get(task_id)
    if estimate is None:
        raise KeyError(f"Task effort was not prepared for task {task_id}.")
    return estimate.effective_hours


def _estimate_task_effort(
    *,
    task: TaskSnapshot,
    historical_tasks: list[HistoricalTaskSummary],
) -> TaskTimeEstimate:
    """Pick manual, historical, blended, or pure-rules effort for one task."""

    rules_baseline_hours = _rules_baseline_hours(task)
    top_matches = _top_history_matches(task=task, historical_tasks=historical_tasks)
    historical_sample_size = len(top_matches)
    historical_median_hours = (
        float(median(match.actual_hours for match in top_matches))
        if top_matches
        else None
    )
    manual_hours = task.estimated_hours

    if manual_hours is not None:
        return TaskTimeEstimate(
            source="manual",
            effective_hours=manual_hours,
            manual_hours=manual_hours,
            rules_baseline_hours=rules_baseline_hours,
            historical_median_hours=historical_median_hours,
            historical_sample_size=historical_sample_size,
        )

    if historical_sample_size >= 3 and historical_median_hours is not None:
        raw_effective_hours = max(1, _round_half_up(historical_median_hours))
        return TaskTimeEstimate(
            source="history",
            effective_hours=_cap_auto_estimate(task=task, raw_effective_hours=raw_effective_hours),
            manual_hours=None,
            rules_baseline_hours=rules_baseline_hours,
            historical_median_hours=historical_median_hours,
            historical_sample_size=historical_sample_size,
        )

    if historical_sample_size >= 1 and historical_median_hours is not None:
        raw_effective_hours = max(
            1,
            _round_half_up((rules_baseline_hours + historical_median_hours) / 2),
        )
        return TaskTimeEstimate(
            source="blended",
            effective_hours=_cap_auto_estimate(task=task, raw_effective_hours=raw_effective_hours),
            manual_hours=None,
            rules_baseline_hours=rules_baseline_hours,
            historical_median_hours=historical_median_hours,
            historical_sample_size=historical_sample_size,
        )

    return TaskTimeEstimate(
        source="rules",
        effective_hours=_cap_auto_estimate(task=task, raw_effective_hours=rules_baseline_hours),
        manual_hours=None,
        rules_baseline_hours=rules_baseline_hours,
        historical_median_hours=None,
        historical_sample_size=0,
    )


def _rules_baseline_hours(task: TaskSnapshot) -> int:
    """Build the deterministic rules-only baseline for one task."""

    if task.requirements:
        baseline_before_priority = ceil(
            sum(requirement.min_level * requirement.weight for requirement in task.requirements) * 2
        )
    else:
        baseline_before_priority = 8

    priority_multiplier = PRIORITY_MULTIPLIERS.get(task.priority, 1.0)
    return max(1, ceil(baseline_before_priority * priority_multiplier))


def _top_history_matches(
    *,
    task: TaskSnapshot,
    historical_tasks: list[HistoricalTaskSummary],
) -> list[HistoricalTaskSummary]:
    """Return the top historical tasks that are similar enough to reuse for effort."""

    scored_matches = [
        (history_task, _history_similarity_score(task=task, history_task=history_task))
        for history_task in historical_tasks
        if _is_history_match(task=task, history_task=history_task)
    ]
    scored_matches.sort(key=lambda item: item[1], reverse=True)
    return [history_task for history_task, _ in scored_matches[:5]]


def _is_history_match(*, task: TaskSnapshot, history_task: HistoricalTaskSummary) -> bool:
    """Allow history reuse when department matches or at least one skill overlaps."""

    shared_skill_ids = _shared_required_skill_ids(task=task, history_task=history_task)
    same_department = bool(task.department_id and task.department_id == history_task.department_id)
    return same_department or bool(shared_skill_ids)


def _history_similarity_score(*, task: TaskSnapshot, history_task: HistoricalTaskSummary) -> int:
    """Score one historical task using the agreed MVP similarity heuristic."""

    shared_skill_ids = _shared_required_skill_ids(task=task, history_task=history_task)
    score = 0
    if task.department_id and task.department_id == history_task.department_id:
        score += 4
    if task.priority == history_task.priority:
        score += 2
    score += len(shared_skill_ids) * 2
    if len(task.requirements) == len(history_task.requirements):
        score += 1
    return score


def _shared_required_skill_ids(
    *,
    task: TaskSnapshot,
    history_task: HistoricalTaskSummary,
) -> set[str]:
    """Return the overlap between current and historical required skill ids."""

    task_skill_ids = {requirement.skill_id for requirement in task.requirements}
    historical_skill_ids = {requirement.skill_id for requirement in history_task.requirements}
    return task_skill_ids & historical_skill_ids


def _round_half_up(value: float) -> int:
    """Avoid Python banker rounding for user-facing hour values."""

    return int(floor(value + 0.5))


def _cap_auto_estimate(*, task: TaskSnapshot, raw_effective_hours: int) -> int:
    """Cap non-manual estimates by the inclusive weekday task window."""

    return min(raw_effective_hours, _window_business_hours(task))


def _window_business_hours(task: TaskSnapshot) -> int:
    """Approximate the task window as 8 hours per weekday, inclusive of due date."""

    business_days = 0
    current_date = task.starts_at.date()
    last_date = (task.ends_at - timedelta(microseconds=1)).date()
    while current_date <= last_date:
        if current_date.weekday() < 5:
            business_days += 1
        current_date += timedelta(days=1)
    return max(1, business_days) * 8
