"""Бизнес-логика утверждения planner proposals в финальные назначения core-service.

Этот файл получает выбранный manager proposal, перечитывает persisted plan run из
planner-service, валидирует его и создает итоговый Assignment вместе с audit log.
Он связывает planner artifacts с final business truth, которая хранится в core.
"""

from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from contracts.schemas import AssignmentProposal, PlanResponse

from .models import Assignment, AssignmentChangeLog, Employee, Task
from .planner_client import PlannerServiceClient

FINAL_TASK_STATUSES = [
    Assignment.Status.APPROVED,
    Assignment.Status.ACTIVE,
    Assignment.Status.COMPLETED,
]


def approve_planner_proposal(
    *,
    task: Task,
    employee: Employee,
    source_plan_run_id: UUID,
    notes: str = "",
    approved_by_user,
    planner_client: PlannerServiceClient | None = None,
) -> Assignment:
    """Validate a persisted planner proposal and create the final core assignment from it."""

    # Repeating the same approval request should be safe for UI retries and network retries.
    existing_assignment = Assignment.objects.filter(task=task, employee=employee, source_plan_run_id=source_plan_run_id).first()
    if existing_assignment is not None:
        return existing_assignment

    # Core reads the persisted planner artifact instead of trusting assignment timing from client payloads.
    plan_run = (planner_client or PlannerServiceClient(settings.PLANNER_SERVICE_URL)).fetch_plan_run(str(source_plan_run_id))
    proposal = _find_matching_proposal(plan_run, str(task.id), str(employee.id))
    _validate_planner_handoff(plan_run, proposal, task, employee)

    with transaction.atomic():
        # Lock the task row so concurrent approvals cannot create two final assignments for the same task.
        Task.objects.select_for_update().get(pk=task.pk)
        existing_assignment = Assignment.objects.filter(
            task=task,
            employee=employee,
            source_plan_run_id=source_plan_run_id,
        ).first()
        if existing_assignment is not None:
            return existing_assignment

        # The task may move through only one final assignee in the MVP approval flow.
        if Assignment.objects.filter(task=task, status__in=FINAL_TASK_STATUSES).exists():
            raise serializers.ValidationError("Task already has a final assignment.")

        assignment = Assignment.objects.create(
            task=task,
            employee=employee,
            source_plan_run_id=source_plan_run_id,
            planned_hours=proposal.planned_hours,
            start_date=proposal.start_date,
            end_date=proposal.end_date,
            status=Assignment.Status.APPROVED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=approved_by_user,
            approved_by_user=approved_by_user,
            approved_at=timezone.now(),
            notes=notes,
        )
        AssignmentChangeLog.objects.create(
            assignment=assignment,
            old_employee=None,
            new_employee=assignment.employee,
            change_reason="Approved persisted planner proposal",
            changed_by_user=approved_by_user,
        )
        return assignment


def _find_matching_proposal(plan_run: PlanResponse, task_id: str, employee_id: str) -> AssignmentProposal:
    """Find the selected solver proposal for the requested task and employee pair."""

    for proposal in plan_run.proposals:
        if proposal.task_id == task_id and proposal.employee_id == employee_id:
            return proposal
    raise serializers.ValidationError("Planner proposal not found for the given task and employee.")


def _validate_planner_handoff(
    plan_run: PlanResponse,
    proposal: AssignmentProposal,
    task: Task,
    employee: Employee,
) -> None:
    """Guard the handoff so core only approves completed and still-eligible planner artifacts."""

    # Approval is allowed only against a completed planner run and a still-proposed candidate pair.
    if plan_run.summary.status != "completed":
        raise serializers.ValidationError("Planner run must be completed before approval.")
    if proposal.status != "proposed":
        raise serializers.ValidationError("Planner proposal is no longer in proposed status.")
    if not proposal.is_selected:
        raise serializers.ValidationError("Planner proposal must be selected before manager approval.")
    # The client supplies a pair to approve, but core re-checks it against planner artifacts before writing business truth.
    if proposal.task_id != str(task.id) or proposal.employee_id != str(employee.id):
        raise serializers.ValidationError("Planner proposal does not match the requested task/employee pair.")
    if proposal.planned_hours is None or proposal.start_date is None or proposal.end_date is None:
        raise serializers.ValidationError("Planner proposal is missing assignment timing data.")
