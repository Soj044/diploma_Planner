"""Planning pipeline: eligibility -> scoring -> CP-SAT optimization -> diagnostics."""

from dataclasses import dataclass
from uuid import uuid4

from contracts.schemas import (
    AssignmentProposal,
    EmployeeSnapshot,
    PlanRequest,
    PlanResponse,
    PlanRunArtifacts,
    PlanRunSummary,
    TaskSnapshot,
    UnassignedTaskDiagnostic,
)
from ortools.sat.python import cp_model

from .repository import utcnow

SCORE_SCALE = 100
ASSIGNMENT_BONUS = 1000


@dataclass(frozen=True)
class EligibilityResult:
    by_task: dict[str, list[str]]


@dataclass(frozen=True)
class ScoreResult:
    by_task: dict[str, dict[str, float]]


def _intervals_overlap(start_a, end_a, start_b, end_b) -> bool:
    return start_a < end_b and start_b < end_a


def _is_available(employee: EmployeeSnapshot, task: TaskSnapshot) -> bool:
    if not employee.availability:
        return False
    for slot in employee.availability:
        if slot.start_at <= task.starts_at and slot.end_at >= task.ends_at:
            return True
    return False


def _meets_requirements(employee: EmployeeSnapshot, task: TaskSnapshot) -> bool:
    for req in task.requirements:
        if employee.skill_levels.get(req.skill_id, 0) < req.min_level:
            return False
    return True


def evaluate_eligibility(employees: list[EmployeeSnapshot], tasks: list[TaskSnapshot]) -> EligibilityResult:
    result: dict[str, list[str]] = {}
    active_employees = [employee for employee in employees if employee.is_active]

    for task in tasks:
        eligible: list[str] = []
        for employee in active_employees:
            if employee.department_id != task.department_id:
                continue
            if not _is_available(employee, task):
                continue
            if not _meets_requirements(employee, task):
                continue
            eligible.append(employee.employee_id)
        result[task.task_id] = eligible

    return EligibilityResult(by_task=result)


def calculate_scores(
    employees: list[EmployeeSnapshot],
    tasks: list[TaskSnapshot],
    eligibility: EligibilityResult,
) -> ScoreResult:
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
            for requirement in task.requirements:
                level = employee.skill_levels.get(requirement.skill_id, 0)
                total_ratio += min(level / requirement.min_level, 2.0)
            task_scores[employee_id] = total_ratio / len(task.requirements)
        scored[task.task_id] = task_scores

    return ScoreResult(by_task=scored)


def build_plan(
    tasks: list[TaskSnapshot],
    employees: list[EmployeeSnapshot],
    eligibility: EligibilityResult,
    scores: ScoreResult,
) -> tuple[list[AssignmentProposal], dict[str, int | float | str]]:
    model = cp_model.CpModel()
    solver = cp_model.CpSolver()

    employee_by_id = {employee.employee_id: employee for employee in employees}
    task_by_id = {task.task_id: task for task in tasks}

    x: dict[tuple[str, str], cp_model.IntVar] = {}
    for task in tasks:
        for employee_id in eligibility.by_task.get(task.task_id, []):
            x[(task.task_id, employee_id)] = model.NewBoolVar(f"x_{task.task_id}_{employee_id}")

    for task in tasks:
        vars_for_task = [x[(task.task_id, e)] for e in eligibility.by_task.get(task.task_id, []) if (task.task_id, e) in x]
        if vars_for_task:
            model.Add(sum(vars_for_task) <= 1)

    for employee in employees:
        eligible_tasks = [task for task in tasks if (task.task_id, employee.employee_id) in x]
        for i in range(len(eligible_tasks)):
            for j in range(i + 1, len(eligible_tasks)):
                first = eligible_tasks[i]
                second = eligible_tasks[j]
                if _intervals_overlap(first.starts_at, first.ends_at, second.starts_at, second.ends_at):
                    model.Add(
                        x[(first.task_id, employee.employee_id)]
                        + x[(second.task_id, employee.employee_id)]
                        <= 1
                    )

    objective_terms = []
    for (task_id, employee_id), decision_var in x.items():
        score = scores.by_task.get(task_id, {}).get(employee_id, 0.0)
        objective_terms.append(decision_var * int(ASSIGNMENT_BONUS + score * SCORE_SCALE))

    if objective_terms:
        model.Maximize(sum(objective_terms))

    status = solver.Solve(model)
    proposals: list[AssignmentProposal] = []

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (task_id, employee_id), decision_var in x.items():
            if solver.Value(decision_var) == 1:
                proposals.append(
                    AssignmentProposal(
                        task_id=task_id,
                        employee_id=employee_id,
                        score=scores.by_task.get(task_id, {}).get(employee_id, 0.0),
                    )
                )

    stats: dict[str, int | float | str] = {
        "status": solver.StatusName(status),
        "num_variables": len(x),
        "num_tasks": len(task_by_id),
        "num_employees": len(employee_by_id),
        "objective_value": solver.ObjectiveValue() if objective_terms else 0,
        "wall_time_sec": solver.WallTime(),
    }
    return proposals, stats


def build_unassigned_diagnostics(
    tasks: list[TaskSnapshot],
    proposals: list[AssignmentProposal],
    eligibility: EligibilityResult,
) -> list[UnassignedTaskDiagnostic]:
    assigned_task_ids = {proposal.task_id for proposal in proposals}
    diagnostics: list[UnassignedTaskDiagnostic] = []

    for task in tasks:
        if task.task_id in assigned_task_ids:
            continue

        eligible = eligibility.by_task.get(task.task_id, [])
        if not eligible:
            diagnostics.append(
                UnassignedTaskDiagnostic(
                    task_id=task.task_id,
                    reason_code="no_eligible_candidates",
                    message="No active candidates satisfy department, availability, and required skills.",
                )
            )
        else:
            diagnostics.append(
                UnassignedTaskDiagnostic(
                    task_id=task.task_id,
                    reason_code="capacity_or_conflict",
                    message="Eligible candidates exist, but scheduling constraints prevented assignment.",
                )
            )

    return diagnostics


def run_planning(request: PlanRequest) -> PlanResponse:
    eligibility = evaluate_eligibility(request.employees, request.tasks)
    scores = calculate_scores(request.employees, request.tasks, eligibility)
    proposals, solver_stats = build_plan(request.tasks, request.employees, eligibility, scores)
    diagnostics = build_unassigned_diagnostics(request.tasks, proposals, eligibility)

    response = PlanResponse(
        summary=PlanRunSummary(
            plan_run_id=str(uuid4()),
            created_at=utcnow(),
            assigned_count=len(proposals),
            unassigned_count=len(diagnostics),
        ),
        proposals=proposals,
        unassigned=diagnostics,
        artifacts=PlanRunArtifacts(
            eligibility=eligibility.by_task,
            scores=scores.by_task,
            solver_statistics=solver_stats,
        ),
    )
    return response
