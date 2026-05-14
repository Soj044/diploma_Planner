"""Explicit task lifecycle workflow rules for manager/admin task edits.

The task update endpoint keeps using the existing DRF viewset, but status and
completion rules live here so task lifecycle behavior stays testable and
separate from serializer/view glue.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework import serializers

from .models import Assignment, Task

FINAL_ASSIGNMENT_STATUSES = (
    Assignment.Status.APPROVED,
    Assignment.Status.ACTIVE,
    Assignment.Status.COMPLETED,
)

IN_PROGRESS_ASSIGNMENT_STATUSES = (
    Assignment.Status.APPROVED,
    Assignment.Status.ACTIVE,
)

DONE_ASSIGNMENT_STATUSES = FINAL_ASSIGNMENT_STATUSES


def create_task(*, validated_data: dict[str, Any]) -> Task:
    """Create a task while enforcing lifecycle invariants on the initial state."""

    target_status = validated_data.get("status", Task.Status.DRAFT)
    target_actual_hours = validated_data.get("actual_hours")
    _validate_actual_hours_state(status=target_status, actual_hours=target_actual_hours)
    _validate_status_preconditions(
        current_status=None,
        target_status=target_status,
        final_assignment=None,
    )
    return Task.objects.create(**validated_data)


def update_task(*, task: Task, validated_data: dict[str, Any]) -> Task:
    """Update a task and synchronize the current final assignment when needed."""

    with transaction.atomic():
        locked_task = Task.objects.select_for_update().get(pk=task.pk)
        target_status = validated_data.get("status", locked_task.status)
        target_actual_hours = validated_data.get("actual_hours", locked_task.actual_hours)
        final_assignment = _get_final_assignment(task=locked_task)

        _validate_actual_hours_state(status=target_status, actual_hours=target_actual_hours)
        _validate_status_preconditions(
            current_status=locked_task.status,
            target_status=target_status,
            final_assignment=final_assignment,
        )

        for field_name, value in validated_data.items():
            setattr(locked_task, field_name, value)
        locked_task.save()
        _sync_final_assignment_status(
            final_assignment=final_assignment,
            target_status=target_status,
        )
        return locked_task


def _validate_actual_hours_state(*, status: str, actual_hours: int | None) -> None:
    """Keep actual task effort empty until the task is explicitly marked done."""

    if status == Task.Status.DONE:
        if actual_hours is None or actual_hours <= 0:
            raise serializers.ValidationError(
                {"actual_hours": "Actual hours must be a positive value when task status is done."}
            )
        return

    if actual_hours is not None:
        raise serializers.ValidationError(
            {"actual_hours": "Actual hours must stay empty unless task status is done."}
        )


def _validate_status_preconditions(
    *,
    current_status: str | None,
    target_status: str,
    final_assignment: Assignment | None,
) -> None:
    """Validate task lifecycle transitions against current final assignment state."""

    if current_status == Task.Status.DONE and target_status != Task.Status.DONE:
        raise serializers.ValidationError(
            {"status": "Done tasks are terminal in MVP and cannot move back to another status."}
        )

    if target_status == Task.Status.IN_PROGRESS:
        if final_assignment is None or final_assignment.status not in IN_PROGRESS_ASSIGNMENT_STATUSES:
            raise serializers.ValidationError(
                {
                    "status": (
                        "Task can move to in_progress only when a final assignment exists in approved or active status."
                    )
                }
            )

    if target_status == Task.Status.DONE:
        if final_assignment is None or final_assignment.status not in DONE_ASSIGNMENT_STATUSES:
            raise serializers.ValidationError(
                {
                    "status": (
                        "Task can move to done only when a final assignment exists in approved, active, or completed status."
                    )
                }
            )


def _get_final_assignment(*, task: Task) -> Assignment | None:
    """Return the single current final assignment for one task or fail on ambiguity."""

    assignments = list(
        Assignment.objects.select_for_update()
        .filter(task=task, status__in=FINAL_ASSIGNMENT_STATUSES)
        .order_by("-id")
    )
    if len(assignments) > 1:
        raise serializers.ValidationError(
            {"status": "Task has multiple final assignments and cannot be updated safely."}
        )
    return assignments[0] if assignments else None


def _sync_final_assignment_status(
    *,
    final_assignment: Assignment | None,
    target_status: str,
) -> None:
    """Apply the agreed forward-only task-to-assignment lifecycle sync in v1."""

    if final_assignment is None:
        return

    if target_status == Task.Status.IN_PROGRESS and final_assignment.status == Assignment.Status.APPROVED:
        final_assignment.status = Assignment.Status.ACTIVE
        final_assignment.save(update_fields=["status"])
        return

    if target_status == Task.Status.DONE and final_assignment.status in (
        Assignment.Status.APPROVED,
        Assignment.Status.ACTIVE,
    ):
        final_assignment.status = Assignment.Status.COMPLETED
        final_assignment.save(update_fields=["status"])
