"""Hard candidate eligibility filters."""

from contracts.schemas import EmployeeSnapshot, TaskSnapshot

from .types import EligibilityResult


def _task_hours(task: TaskSnapshot) -> int:
    if task.estimated_hours:
        return task.estimated_hours
    seconds = (task.ends_at - task.starts_at).total_seconds()
    return max(1, int((seconds + 3599) // 3600))


def _is_available(employee: EmployeeSnapshot, task: TaskSnapshot) -> bool:
    if not employee.availability:
        return False
    for slot in employee.availability:
        if slot.start_at <= task.starts_at and slot.end_at >= task.ends_at:
            if slot.available_hours is not None and slot.available_hours < _task_hours(task):
                continue
            return True
    return False


def _meets_requirements(employee: EmployeeSnapshot, task: TaskSnapshot) -> bool:
    for requirement in task.requirements:
        if employee.skill_levels.get(requirement.skill_id, 0) < requirement.min_level:
            return False
    return True


def evaluate_eligibility(employees: list[EmployeeSnapshot], tasks: list[TaskSnapshot]) -> EligibilityResult:
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
