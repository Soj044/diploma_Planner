"""Жесткие фильтры допустимости кандидатов для назначения на задачу.

Этот файл отбрасывает сотрудников, которые не подходят по департаменту,
доступности и обязательным навыкам. Его результат используется scoring,
optimizer и diagnostics внутри planning pipeline.
"""

from contracts.schemas import EmployeeSnapshot, TaskSnapshot

from .types import EligibilityResult


def _task_hours(task: TaskSnapshot) -> int:
    """Normalize task duration to whole planning hours for capacity checks."""

    if task.estimated_hours:
        return task.estimated_hours
    seconds = (task.ends_at - task.starts_at).total_seconds()
    return max(1, int((seconds + 3599) // 3600))


def _is_available(employee: EmployeeSnapshot, task: TaskSnapshot) -> bool:
    """Require one availability slot that covers the whole task interval."""

    if not employee.availability:
        return False
    for slot in employee.availability:
        # The MVP planner treats partial overlap as unavailable; one slot must cover the full task window.
        if slot.start_at <= task.starts_at and slot.end_at >= task.ends_at:
            if slot.available_hours is not None and slot.available_hours < _task_hours(task):
                continue
            return True
    return False


def _meets_requirements(employee: EmployeeSnapshot, task: TaskSnapshot) -> bool:
    """Check that the employee meets every required skill threshold."""

    for requirement in task.requirements:
        if employee.skill_levels.get(requirement.skill_id, 0) < requirement.min_level:
            return False
    return True


def evaluate_eligibility(employees: list[EmployeeSnapshot], tasks: list[TaskSnapshot]) -> EligibilityResult:
    """Apply hard business filters before scoring or optimization starts."""

    result: dict[str, list[str]] = {}
    active_employees = [employee for employee in employees if employee.is_active]

    for task in tasks:
        eligible: list[str] = []
        for employee in active_employees:
            if task.department_id and employee.department_id != task.department_id:
                continue
            if not _is_available(employee, task):
                continue
            if not _meets_requirements(employee, task):
                continue
            eligible.append(employee.employee_id)
        result[task.task_id] = eligible

    return EligibilityResult(by_task=result)
