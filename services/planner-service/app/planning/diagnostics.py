"""Diagnostics for tasks that remain unassigned after optimization."""

from contracts.schemas import AssignmentProposal, TaskSnapshot, UnassignedTaskDiagnostic

from .types import EligibilityResult


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
