"""Оркестрация planning pipeline от snapshot до proposals и diagnostics.

Этот файл последовательно запускает eligibility, scoring, optimizer и
diagnostics, затем собирает итоговый PlanResponse. Он связывает внутренние
planning модули в один воспроизводимый расчет назначений.
"""

from uuid import uuid4

from contracts.schemas import PlanResponse, PlanRunArtifacts, PlanRunSummary, PlanningSnapshot

from .analysis import build_candidate_analysis
from .diagnostics import build_unassigned_diagnostics
from .eligibility import evaluate_eligibility
from .optimizer import build_plan
from .scoring import calculate_scores
from .time import utcnow
from .time_estimation import build_task_effort_map


def run_planning(snapshot: PlanningSnapshot) -> PlanResponse:
    """Run the full planner pipeline from hard filters to solver artifacts."""

    task_effort_map = build_task_effort_map(snapshot.tasks, snapshot.historical_tasks)
    eligibility = evaluate_eligibility(snapshot.employees, snapshot.tasks, task_effort_map)
    scores = calculate_scores(snapshot.employees, snapshot.tasks, eligibility)
    proposals, solver_stats = build_plan(
        snapshot.tasks,
        snapshot.employees,
        eligibility,
        scores,
        task_effort_map,
    )
    diagnostics = build_unassigned_diagnostics(snapshot.tasks, proposals, eligibility)
    candidate_analysis = build_candidate_analysis(snapshot.tasks, eligibility, scores, proposals)

    return PlanResponse(
        summary=PlanRunSummary(
            plan_run_id=str(uuid4()),
            status="completed",
            created_at=utcnow(),
            planning_period_start=snapshot.planning_period_start,
            planning_period_end=snapshot.planning_period_end,
            assigned_count=len(proposals),
            unassigned_count=len(diagnostics),
        ),
        proposals=proposals,
        unassigned=diagnostics,
        artifacts=PlanRunArtifacts(
            eligibility=eligibility.by_task,
            scores=scores.by_task,
            solver_statistics=solver_stats,
            candidate_analysis=candidate_analysis,
            time_estimates=task_effort_map,
        ),
    )
