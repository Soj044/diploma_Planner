"""Диагностика причин, по которым задача осталась без назначения.

Этот файл объясняет, почему planner не выдал proposal для конкретной задачи:
из-за отсутствия eligible кандидатов или из-за конфликтов расписания. Его
результат используется в final PlanResponse и manager review.
"""

from contracts.schemas import AssignmentProposal, TaskSnapshot, UnassignedTaskDiagnostic

from .types import EligibilityResult


def build_unassigned_diagnostics(
    tasks: list[TaskSnapshot],
    proposals: list[AssignmentProposal],
    eligibility: EligibilityResult,
) -> list[UnassignedTaskDiagnostic]:
    """Explain whether a task failed at eligibility or later scheduling constraints."""

    assigned_task_ids = {proposal.task_id for proposal in proposals}
    diagnostics: list[UnassignedTaskDiagnostic] = []

    for task in tasks:
        if task.task_id in assigned_task_ids:
            continue

        eligible = eligibility.by_task.get(task.task_id, [])
        if not eligible:
            # No candidate survived hard filters, so the task failed before optimization started.
            diagnostics.append(
                UnassignedTaskDiagnostic(
                    task_id=task.task_id,
                    reason_code="no_eligible_candidates",
                    message="No active candidates satisfy department, availability, and required skills.",
                )
            )
        else:
            # Candidates existed, but optimization could not place the task without conflicts.
            diagnostics.append(
                UnassignedTaskDiagnostic(
                    task_id=task.task_id,
                    reason_code="capacity_or_conflict",
                    message="Eligible candidates exist, but scheduling constraints prevented assignment.",
                )
            )

    return diagnostics
