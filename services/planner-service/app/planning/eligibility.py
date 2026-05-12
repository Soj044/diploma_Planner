"""Жесткие фильтры допустимости кандидатов для назначения на задачу.

Этот файл отбрасывает сотрудников, которые не подходят по департаменту,
доступности и обязательным навыкам. Его результат используется scoring,
optimizer и diagnostics внутри planning pipeline.
"""

from contracts.schemas import EmployeeSnapshot, TaskSnapshot

from .types import CandidateEligibilityTrace, EligibilityResult


def _task_hours(task: TaskSnapshot) -> int:
    """Normalize task duration to whole planning hours for capacity checks."""

    if task.estimated_hours:
        return task.estimated_hours
    seconds = (task.ends_at - task.starts_at).total_seconds()
    return max(1, int((seconds + 3599) // 3600))


def _slot_available_hours(employee: EmployeeSnapshot, task: TaskSnapshot) -> float:
    """Sum all available hours contributed by slots intersecting the task window."""

    total_hours = 0.0
    for slot in employee.availability:
        overlap_start = max(slot.start_at, task.starts_at)
        overlap_end = min(slot.end_at, task.ends_at)
        if overlap_start >= overlap_end:
            continue
        if slot.available_hours is not None:
            total_hours += slot.available_hours
            continue
        total_hours += (overlap_end - overlap_start).total_seconds() / 3600
    return total_hours


def _missing_skill_ids(employee: EmployeeSnapshot, task: TaskSnapshot) -> list[str]:
    """Return every required skill the employee fails to satisfy."""

    return [
        requirement.skill_id
        for requirement in task.requirements
        if employee.skill_levels.get(requirement.skill_id, 0) < requirement.min_level
    ]


def _candidate_trace(employee: EmployeeSnapshot, task: TaskSnapshot) -> CandidateEligibilityTrace:
    """Build one hard-filter trace that planner can later reuse for explanations."""

    required_hours = _task_hours(task)
    available_hours = _slot_available_hours(employee, task) if employee.availability else 0.0
    missing_skill_ids = _missing_skill_ids(employee, task)
    matched_department = not task.department_id or employee.department_id == task.department_id
    eligible = (
        employee.is_active
        and matched_department
        and available_hours >= required_hours
        and not missing_skill_ids
    )
    return CandidateEligibilityTrace(
        employee_id=employee.employee_id,
        is_active=employee.is_active,
        matched_department=matched_department,
        eligible=eligible,
        available_hours_in_window=available_hours,
        required_hours=required_hours,
        missing_skill_ids=missing_skill_ids,
    )


def evaluate_eligibility(employees: list[EmployeeSnapshot], tasks: list[TaskSnapshot]) -> EligibilityResult:
    """Apply hard business filters before scoring or optimization starts."""

    result: dict[str, list[str]] = {}
    traces_by_task: dict[str, list[CandidateEligibilityTrace]] = {}

    for task in tasks:
        eligible: list[str] = []
        task_traces: list[CandidateEligibilityTrace] = []
        for employee in employees:
            trace = _candidate_trace(employee, task)
            task_traces.append(trace)
            if trace.eligible:
                eligible.append(employee.employee_id)
        result[task.task_id] = eligible
        traces_by_task[task.task_id] = task_traces

    return EligibilityResult(by_task=result, traces_by_task=traces_by_task)
