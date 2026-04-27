"""Оркестрация planning pipeline от snapshot до proposals и diagnostics.

Этот файл последовательно запускает eligibility, scoring, optimizer и
diagnostics, затем собирает итоговый PlanResponse. Он связывает внутренние
planning модули в один воспроизводимый расчет назначений.
"""

from uuid import uuid4

from contracts.schemas import PlanResponse, PlanRunArtifacts, PlanRunSummary, PlanningSnapshot

from .diagnostics import build_unassigned_diagnostics
from .eligibility import evaluate_eligibility
from .optimizer import build_plan
from .scoring import calculate_scores
from .time import utcnow


def run_planning(snapshot: PlanningSnapshot) -> PlanResponse:
    """Run the full planner pipeline from hard filters to solver artifacts."""

    eligibility = evaluate_eligibility(snapshot.employees, snapshot.tasks)
    scores = calculate_scores(snapshot.employees, snapshot.tasks, eligibility)
    proposals, solver_stats = build_plan(snapshot.tasks, snapshot.employees, eligibility, scores)
    diagnostics = build_unassigned_diagnostics(snapshot.tasks, proposals, eligibility)

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
        ),
    )
