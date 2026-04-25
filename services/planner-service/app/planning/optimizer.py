"""CP-SAT assignment optimization."""

from math import ceil

from contracts.schemas import AssignmentProposal, EmployeeSnapshot, TaskSnapshot
from ortools.sat.python import cp_model

from .types import EligibilityResult, ScoreResult

SCORE_SCALE = 100
ASSIGNMENT_BONUS = 1000


def _intervals_overlap(start_a, end_a, start_b, end_b) -> bool:
    """Return whether two task windows intersect for the same employee."""

    return start_a < end_b and start_b < end_a


def _planned_hours(task: TaskSnapshot) -> int:
    """Derive assignment effort in whole hours when the task omits an explicit estimate."""

    if task.estimated_hours:
        return task.estimated_hours
    duration_seconds = max((task.ends_at - task.starts_at).total_seconds(), 0)
    return max(1, ceil(duration_seconds / 3600))


def build_plan(
    tasks: list[TaskSnapshot],
    employees: list[EmployeeSnapshot],
    eligibility: EligibilityResult,
    scores: ScoreResult,
) -> tuple[list[AssignmentProposal], dict[str, int | float | str]]:
    """Choose the best non-conflicting employee-task assignments with CP-SAT."""

    model = cp_model.CpModel()
    solver = cp_model.CpSolver()

    x: dict[tuple[str, str], cp_model.IntVar] = {}
    for task in tasks:
        for employee_id in eligibility.by_task.get(task.task_id, []):
            x[(task.task_id, employee_id)] = model.NewBoolVar(f"x_{task.task_id}_{employee_id}")

    for task in tasks:
        vars_for_task = [
            x[(task.task_id, employee_id)]
            for employee_id in eligibility.by_task.get(task.task_id, [])
            if (task.task_id, employee_id) in x
        ]
        if vars_for_task:
            # One task can be assigned to at most one employee in the current MVP.
            model.Add(sum(vars_for_task) <= 1)

    for employee in employees:
        eligible_tasks = [task for task in tasks if (task.task_id, employee.employee_id) in x]
        for first_index in range(len(eligible_tasks)):
            for second_index in range(first_index + 1, len(eligible_tasks)):
                first = eligible_tasks[first_index]
                second = eligible_tasks[second_index]
                if _intervals_overlap(first.starts_at, first.ends_at, second.starts_at, second.ends_at):
                    # The same employee cannot hold two overlapping task windows.
                    model.Add(
                        x[(first.task_id, employee.employee_id)]
                        + x[(second.task_id, employee.employee_id)]
                        <= 1
                    )

    objective_terms = []
    for (task_id, employee_id), decision_var in x.items():
        score = scores.by_task.get(task_id, {}).get(employee_id, 0.0)
        # The bonus makes solver prioritize covering more tasks before fine-tuning by score.
        objective_terms.append(decision_var * int(ASSIGNMENT_BONUS + score * SCORE_SCALE))

    if objective_terms:
        model.Maximize(sum(objective_terms))

    status = solver.Solve(model)
    task_by_id = {task.task_id: task for task in tasks}
    proposals: list[AssignmentProposal] = []

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (task_id, employee_id), decision_var in x.items():
            if solver.Value(decision_var) == 1:
                task = task_by_id[task_id]
                proposals.append(
                    AssignmentProposal(
                        task_id=task_id,
                        employee_id=employee_id,
                        score=scores.by_task.get(task_id, {}).get(employee_id, 0.0),
                        planned_hours=_planned_hours(task),
                        start_date=task.starts_at.date(),
                        end_date=task.ends_at.date(),
                    )
                )

    stats: dict[str, int | float | str] = {
        "status": solver.StatusName(status),
        "num_variables": len(x),
        "num_tasks": len(tasks),
        "num_employees": len(employees),
        "objective_value": solver.ObjectiveValue() if objective_terms else 0,
        "wall_time_sec": solver.WallTime(),
    }
    return proposals, stats
