"""Deterministic candidate scoring."""

from contracts.schemas import EmployeeSnapshot, TaskSnapshot

from .types import EligibilityResult, ScoreResult


def calculate_scores(
    employees: list[EmployeeSnapshot],
    tasks: list[TaskSnapshot],
    eligibility: EligibilityResult,
) -> ScoreResult:
    """Score eligible candidates so the optimizer can prefer stronger matches."""

    employee_by_id = {employee.employee_id: employee for employee in employees}
    scored: dict[str, dict[str, float]] = {}

    for task in tasks:
        task_scores: dict[str, float] = {}
        for employee_id in eligibility.by_task.get(task.task_id, []):
            employee = employee_by_id[employee_id]
            if not task.requirements:
                task_scores[employee_id] = 1.0
                continue

            total_ratio = 0.0
            total_weight = 0.0
            for requirement in task.requirements:
                level = employee.skill_levels.get(requirement.skill_id, 0)
                weight = requirement.weight
                # Overskilled candidates may get a boost, but the cap keeps one skill from dominating the result.
                total_ratio += min(level / requirement.min_level, 2.0) * weight
                total_weight += weight
            task_scores[employee_id] = total_ratio / max(total_weight, 1.0)
        scored[task.task_id] = task_scores

    return ScoreResult(by_task=scored)
