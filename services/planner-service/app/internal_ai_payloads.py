"""Derived internal AI read models for planner-service.

This module turns persisted planner artifacts into internal-only payloads for
ai-layer indexing and explanation context. It preserves planner-service as the
source of truth for proposals, diagnostics, eligibility, scores, and solver
artifacts without exposing these helper shapes to browsers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from contracts.schemas import AssignmentProposal, CandidateAnalysisRow, TaskSnapshot, UnassignedTaskDiagnostic

from app.infrastructure.repositories.sqlite import PersistedPlanRunRecord, SqlitePlanRunRepository


def build_unassigned_index_feed(
    repository: SqlitePlanRunRepository,
    changed_since: datetime | None,
) -> dict[str, Any]:
    """Build the flattened `unassigned_case` feed used by ai-layer retrieval sync."""

    generated_at = datetime.now(tz=UTC)
    items: list[dict[str, Any]] = []

    for record in repository.list_completed_records(changed_since):
        for diagnostic in record.response.unassigned:
            task_snapshot = _find_task_snapshot(record, diagnostic.task_id)
            time_estimate = record.response.artifacts.time_estimates.get(diagnostic.task_id)
            eligibility = list(record.response.artifacts.eligibility.get(diagnostic.task_id, []))
            score_map = {
                employee_id: float(score)
                for employee_id, score in record.response.artifacts.scores.get(diagnostic.task_id, {}).items()
            }
            candidate_analysis = list(record.response.artifacts.candidate_analysis.get(diagnostic.task_id, []))
            items.append(
                {
                    "source_type": "unassigned_case",
                    "source_key": f"unassigned:{record.plan_run_id}:{diagnostic.task_id}",
                    "index_action": "upsert",
                    "title": _unassigned_case_title(task_snapshot, diagnostic),
                    "content": _unassigned_case_content(
                        record=record,
                        task_snapshot=task_snapshot,
                        diagnostic=diagnostic,
                        eligibility=eligibility,
                        score_map=score_map,
                        candidate_analysis=candidate_analysis,
                        time_estimate=time_estimate.model_dump(mode="json") if time_estimate else None,
                    ),
                    "metadata": {
                        "plan_run_id": record.plan_run_id,
                        "task_id": diagnostic.task_id,
                        "reason_code": diagnostic.reason_code,
                        "eligible_employee_ids": eligibility,
                        "eligible_count": len(eligibility),
                        "score_map": score_map,
                        "time_estimate": time_estimate.model_dump(mode="json") if time_estimate else None,
                        **_candidate_analysis_breakdown(candidate_analysis),
                    },
                    "source_updated_at": record.created_at.isoformat(),
                }
            )

    next_changed_since = (
        max((item["source_updated_at"] for item in items), default=None)
        or (changed_since.isoformat() if changed_since else generated_at.isoformat())
    )
    return {
        "source_service": "planner-service",
        "generated_at": generated_at.isoformat(),
        "next_changed_since": next_changed_since,
        "items": items,
    }


def build_proposal_context(
    repository: SqlitePlanRunRepository,
    *,
    plan_run_id: str,
    task_id: str,
    employee_id: str,
) -> dict[str, Any]:
    """Build the persisted proposal explanation context for one task/employee pair."""

    record = repository.get_record(plan_run_id)
    if record is None:
        raise LookupError("Plan run was not found.")

    task_snapshot = _find_task_snapshot(record, task_id)
    target_proposal = _find_target_proposal(record, task_id, employee_id)
    sibling_proposals = [
        _proposal_payload(proposal)
        for proposal in record.response.proposals
        if proposal.task_id == task_id and proposal.employee_id != employee_id
    ]
    eligibility = list(record.response.artifacts.eligibility.get(task_id, []))
    score_map = {
        candidate_id: float(score)
        for candidate_id, score in record.response.artifacts.scores.get(task_id, {}).items()
    }
    candidate_analysis = list(record.response.artifacts.candidate_analysis.get(task_id, []))
    time_estimate = record.response.artifacts.time_estimates.get(task_id)
    return {
        "plan_run_summary": _plan_run_summary_payload(record),
        "task_snapshot": _task_snapshot_payload(task_snapshot),
        "proposal": _proposal_payload(target_proposal),
        "sibling_proposals": sibling_proposals,
        "eligibility": {
            "employee_ids": eligibility,
            "eligible_count": len(eligibility),
        },
        "score_map": score_map,
        "candidate_analysis": [_candidate_analysis_payload(row) for row in candidate_analysis],
        "selected_employee_id": target_proposal.employee_id,
        "selected_score": float(target_proposal.score),
        "solver_summary": record.response.artifacts.solver_statistics,
        "time_estimate": time_estimate.model_dump(mode="json") if time_estimate else None,
    }


def build_unassigned_context(
    repository: SqlitePlanRunRepository,
    *,
    plan_run_id: str,
    task_id: str,
) -> dict[str, Any]:
    """Build the persisted unassigned-task explanation context for one task."""

    record = repository.get_record(plan_run_id)
    if record is None:
        raise LookupError("Plan run was not found.")

    task_snapshot = _find_task_snapshot(record, task_id)
    diagnostic = _find_unassigned_diagnostic(record, task_id)
    eligibility = list(record.response.artifacts.eligibility.get(task_id, []))
    score_map = {
        candidate_id: float(score)
        for candidate_id, score in record.response.artifacts.scores.get(task_id, {}).items()
    }
    candidate_analysis = list(record.response.artifacts.candidate_analysis.get(task_id, []))
    time_estimate = record.response.artifacts.time_estimates.get(task_id)
    return {
        "plan_run_summary": _plan_run_summary_payload(record),
        "task_snapshot": _task_snapshot_payload(task_snapshot),
        "diagnostic": _diagnostic_payload(diagnostic),
        "eligibility": {
            "employee_ids": eligibility,
            "eligible_count": len(eligibility),
        },
        "score_map": score_map,
        "candidate_analysis": [_candidate_analysis_payload(row) for row in candidate_analysis],
        "solver_summary": record.response.artifacts.solver_statistics,
        "time_estimate": time_estimate.model_dump(mode="json") if time_estimate else None,
    }


def _find_task_snapshot(record: PersistedPlanRunRecord, task_id: str) -> TaskSnapshot:
    """Return the persisted task snapshot for one task identifier."""

    for task_snapshot in record.snapshot.tasks:
        if task_snapshot.task_id == task_id:
            return task_snapshot
    raise LookupError("Task snapshot was not found in the persisted plan run.")


def _find_target_proposal(
    record: PersistedPlanRunRecord,
    task_id: str,
    employee_id: str,
) -> AssignmentProposal:
    """Return the persisted proposal selected by task and employee identifiers."""

    for proposal in record.response.proposals:
        if proposal.task_id == task_id and proposal.employee_id == employee_id:
            return proposal
    raise LookupError("Proposal was not found in the persisted plan run.")


def _find_unassigned_diagnostic(
    record: PersistedPlanRunRecord,
    task_id: str,
) -> UnassignedTaskDiagnostic:
    """Return the persisted unassigned diagnostic for one task identifier."""

    for diagnostic in record.response.unassigned:
        if diagnostic.task_id == task_id:
            return diagnostic
    raise LookupError("Unassigned diagnostic was not found in the persisted plan run.")


def _plan_run_summary_payload(record: PersistedPlanRunRecord) -> dict[str, Any]:
    """Serialize one persisted plan run summary for internal AI context routes."""

    summary = record.response.summary
    return {
        "plan_run_id": summary.plan_run_id,
        "status": summary.status,
        "created_at": summary.created_at.isoformat(),
        "planning_period_start": summary.planning_period_start.isoformat(),
        "planning_period_end": summary.planning_period_end.isoformat(),
        "assigned_count": summary.assigned_count,
        "unassigned_count": summary.unassigned_count,
        "department_id": record.department_id,
        "initiated_by_user_id": record.initiated_by_user_id,
    }


def _task_snapshot_payload(task_snapshot: TaskSnapshot) -> dict[str, Any]:
    """Serialize one persisted task snapshot for internal AI context routes."""

    return {
        "task_id": task_snapshot.task_id,
        "department_id": task_snapshot.department_id,
        "title": task_snapshot.title,
        "priority": task_snapshot.priority,
        "starts_at": task_snapshot.starts_at.isoformat(),
        "ends_at": task_snapshot.ends_at.isoformat(),
        "estimated_hours": task_snapshot.estimated_hours,
        "requirements": [
            {
                "skill_id": requirement.skill_id,
                "min_level": requirement.min_level,
                "weight": float(requirement.weight),
            }
            for requirement in task_snapshot.requirements
        ],
    }


def _proposal_payload(proposal: AssignmentProposal) -> dict[str, Any]:
    """Serialize one persisted assignment proposal for internal AI context routes."""

    return {
        "task_id": proposal.task_id,
        "employee_id": proposal.employee_id,
        "score": proposal.score,
        "proposal_rank": proposal.proposal_rank,
        "is_selected": proposal.is_selected,
        "planned_hours": proposal.planned_hours,
        "start_date": proposal.start_date.isoformat() if proposal.start_date else None,
        "end_date": proposal.end_date.isoformat() if proposal.end_date else None,
        "status": proposal.status,
        "explanation_text": proposal.explanation_text,
    }


def _candidate_analysis_payload(row: CandidateAnalysisRow) -> dict[str, Any]:
    """Serialize one persisted candidate comparison row for internal AI readers."""

    return row.model_dump(mode="json")


def _diagnostic_payload(diagnostic: UnassignedTaskDiagnostic) -> dict[str, Any]:
    """Serialize one persisted unassigned diagnostic for internal AI context routes."""

    return {
        "task_id": diagnostic.task_id,
        "reason_code": diagnostic.reason_code,
        "message": diagnostic.message,
        "reason_details": diagnostic.reason_details,
    }


def _unassigned_case_title(task_snapshot: TaskSnapshot, diagnostic: UnassignedTaskDiagnostic) -> str:
    """Build a compact title for one persisted unassigned retrieval case."""

    return f"{task_snapshot.title} -> {diagnostic.reason_code}"


def _unassigned_case_content(
    *,
    record: PersistedPlanRunRecord,
    task_snapshot: TaskSnapshot,
    diagnostic: UnassignedTaskDiagnostic,
    eligibility: list[str],
    score_map: dict[str, float],
    candidate_analysis: list[CandidateAnalysisRow],
    time_estimate: dict[str, Any] | None,
) -> str:
    """Build a flattened retrieval body for one persisted unassigned case."""

    requirement_lines = [
        f"- {requirement.skill_id}: min_level={requirement.min_level}, weight={float(requirement.weight):.2f}"
        for requirement in task_snapshot.requirements
    ]
    score_lines = [f"- {employee_id}: {score:.4f}" for employee_id, score in score_map.items()]
    solver_status = record.response.artifacts.solver_statistics.get("status", "unknown")
    breakdown = _candidate_analysis_breakdown(candidate_analysis)
    return "\n".join(
        [
            f"Plan run id: {record.plan_run_id}",
            f"Task: {task_snapshot.title}",
            f"Task department: {task_snapshot.department_id or 'n/a'}",
            f"Task window: {task_snapshot.starts_at.isoformat()} -> {task_snapshot.ends_at.isoformat()}",
            f"Task estimated hours: {task_snapshot.estimated_hours}",
            f"Task priority: {task_snapshot.priority}",
            f"Planner time estimate: {time_estimate or 'n/a'}",
            "Task requirements:",
            *(requirement_lines or ["- none"]),
            f"Diagnostic reason: {diagnostic.reason_code}",
            f"Diagnostic message: {diagnostic.message}",
            f"Diagnostic details: {diagnostic.reason_details or 'n/a'}",
            f"Eligible employee ids ({len(eligibility)}): {', '.join(eligibility) if eligibility else 'none'}",
            (
                "Candidate analysis breakdown: "
                f"availability_rejections={breakdown['rejected_insufficient_availability_count']}, "
                f"skill_rejections={breakdown['rejected_missing_skill_count']}, "
                f"eligible_conflicts={breakdown['eligible_conflict_count']}, "
                f"lower_score_alternatives={breakdown['eligible_lower_score_count']}"
            ),
            "Score map:",
            *(score_lines or ["- none"]),
            f"Solver status: {solver_status}",
        ]
    )


def _candidate_analysis_breakdown(candidate_analysis: list[CandidateAnalysisRow]) -> dict[str, int]:
    """Summarize candidate outcomes into short retrieval-friendly counters."""

    breakdown = {
        "rejected_missing_skill_count": 0,
        "rejected_insufficient_availability_count": 0,
        "eligible_conflict_count": 0,
        "eligible_lower_score_count": 0,
    }
    for row in candidate_analysis:
        if row.outcome_code == "rejected_missing_required_skill":
            breakdown["rejected_missing_skill_count"] += 1
        elif row.outcome_code == "rejected_insufficient_available_hours":
            breakdown["rejected_insufficient_availability_count"] += 1
        elif row.outcome_code == "eligible_not_selected_capacity_or_conflict":
            breakdown["eligible_conflict_count"] += 1
        elif row.outcome_code == "eligible_not_selected_lower_score":
            breakdown["eligible_lower_score_count"] += 1
    return breakdown
