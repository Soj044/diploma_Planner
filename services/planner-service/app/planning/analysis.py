"""Deterministic candidate comparison facts derived from planner pipeline results.

This module converts eligibility traces, persisted scores, and optimizer output
into stable per-candidate analysis rows. The resulting facts are stored with
plan runs and later reused by ai-layer explanations without asking the LLM to
infer hard planner outcomes on its own.
"""

from __future__ import annotations

from contracts.schemas import AssignmentProposal, CandidateAnalysisRow, TaskSnapshot

from .types import EligibilityResult, ScoreResult


def build_candidate_analysis(
    tasks: list[TaskSnapshot],
    eligibility: EligibilityResult,
    scores: ScoreResult,
    proposals: list[AssignmentProposal],
) -> dict[str, list[CandidateAnalysisRow]]:
    """Build persisted per-task candidate comparison rows for AI explanations."""

    selected_by_task = {
        proposal.task_id: proposal
        for proposal in proposals
        if proposal.is_selected
    }
    analysis: dict[str, list[CandidateAnalysisRow]] = {}

    for task in tasks:
        traces = eligibility.traces_by_task.get(task.task_id, [])
        selected_proposal = selected_by_task.get(task.task_id)
        selected_score = selected_proposal.score if selected_proposal is not None else None
        selected_employee_id = selected_proposal.employee_id if selected_proposal is not None else None
        rows = [
            CandidateAnalysisRow(
                employee_id=trace.employee_id,
                outcome_code=_determine_outcome_code(
                    trace=trace,
                    selected_employee_id=selected_employee_id,
                    selected_score=selected_score,
                    score=scores.by_task.get(task.task_id, {}).get(trace.employee_id),
                ),
                eligible=trace.eligible,
                score=scores.by_task.get(task.task_id, {}).get(trace.employee_id),
                selected=trace.employee_id == selected_employee_id,
                available_hours_in_window=round(trace.available_hours_in_window, 2),
                required_hours=trace.required_hours,
                missing_skill_ids=list(trace.missing_skill_ids),
                missing_skill_names=list(trace.missing_skill_names),
                matched_department=trace.matched_department,
            )
            for trace in traces
        ]
        analysis[task.task_id] = sorted(rows, key=_candidate_sort_key)

    return analysis


def _determine_outcome_code(
    *,
    trace,
    selected_employee_id: str | None,
    selected_score: float | None,
    score: float | None,
) -> str:
    """Classify one candidate outcome using hard filters, scores, and selection."""

    if selected_employee_id == trace.employee_id:
        return "selected"
    if trace.eligible:
        if selected_employee_id is None:
            return "eligible_not_selected_capacity_or_conflict"
        if score is not None and selected_score is not None and score < selected_score:
            return "eligible_not_selected_lower_score"
        return "eligible_not_selected_capacity_or_conflict"
    if not trace.is_active:
        return "rejected_inactive_employee"
    if not trace.matched_department:
        return "rejected_department_mismatch"
    if trace.missing_skill_ids:
        return "rejected_missing_required_skill"
    return "rejected_insufficient_available_hours"


def _candidate_sort_key(row: CandidateAnalysisRow) -> tuple[int, float, str]:
    """Keep candidate analysis rows in a stable explanation-friendly order."""

    priority_map = {
        "selected": 0,
        "eligible_not_selected_lower_score": 1,
        "eligible_not_selected_capacity_or_conflict": 2,
        "rejected_insufficient_available_hours": 3,
        "rejected_missing_required_skill": 4,
        "rejected_department_mismatch": 5,
        "rejected_inactive_employee": 6,
    }
    score = row.score if row.score is not None else -1.0
    return (priority_map.get(row.outcome_code, 99), -score, row.employee_id)
