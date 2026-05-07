"""Derived internal AI read-model builders for core-service.

This module builds the flattened `assignment_case` feed and the live
task-plus-employee context that `ai-layer` uses for retrieval and explanations.
The payloads stay internal-only and do not create a second business truth.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone

from .models import (
    Assignment,
    Employee,
    EmployeeAvailabilityOverride,
    EmployeeLeave,
    EmployeeSkill,
    Task,
    TaskRequirement,
    WorkSchedule,
    WorkScheduleDay,
)

AI_SUCCESS_ASSIGNMENT_STATUSES = {
    Assignment.Status.APPROVED,
    Assignment.Status.ACTIVE,
    Assignment.Status.COMPLETED,
}
AI_DELETE_ASSIGNMENT_STATUSES = {
    Assignment.Status.REJECTED,
    Assignment.Status.CANCELLED,
}


def build_assignment_index_feed(changed_since: datetime | None) -> dict[str, Any]:
    """Build the internal flattened `assignment_case` feed for ai-layer sync."""

    generated_at = timezone.now()
    items: list[dict[str, Any]] = []

    for assignment in _get_assignment_case_queryset(changed_since):
        source_updated_at = _assignment_source_updated_at(assignment)
        items.append(
            {
                "source_type": "assignment_case",
                "source_key": f"assignment:{assignment.id}",
                "index_action": _assignment_index_action(assignment),
                "title": _assignment_case_title(assignment),
                "content": _assignment_case_content(assignment),
                "metadata": _assignment_case_metadata(assignment),
                "source_updated_at": source_updated_at.isoformat(),
            }
        )

    next_changed_since = (
        max((item["source_updated_at"] for item in items), default=None)
        or (changed_since.isoformat() if changed_since else generated_at.isoformat())
    )

    return {
        "source_service": "core-service",
        "generated_at": generated_at.isoformat(),
        "next_changed_since": next_changed_since,
        "items": items,
    }


def build_assignment_context(*, task_id: int, employee_id: int) -> dict[str, Any]:
    """Build the live assignment explanation context for one task and employee pair."""

    task = _get_task_for_ai_context(task_id)
    employee = _get_employee_for_ai_context(employee_id)
    window_start, window_end = _task_window(task)
    default_schedule = _get_default_schedule(employee)
    relevant_weekdays = _window_weekdays(window_start, window_end)

    return {
        "task": {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "estimated_hours": task.estimated_hours,
            "start_date": window_start.isoformat(),
            "due_date": task.due_date.isoformat(),
            "department_id": str(task.department_id) if task.department_id else None,
            "department_name": task.department.name if task.department else None,
        },
        "requirements": [_requirement_payload(requirement) for requirement in task.requirements.all()],
        "employee": {
            "id": str(employee.id),
            "full_name": employee.full_name,
            "position_name": employee.position_name,
            "department_id": str(employee.department_id) if employee.department_id else None,
            "department_name": employee.department.name if employee.department else None,
            "employment_type": employee.employment_type,
            "weekly_capacity_hours": employee.weekly_capacity_hours,
            "timezone": employee.timezone,
            "is_active": employee.is_active,
        },
        "employee_skills": [_employee_skill_payload(skill) for skill in employee.skills.all()],
        "availability": {
            "default_schedule_id": str(default_schedule.id) if default_schedule else None,
            "default_schedule_name": default_schedule.name if default_schedule else None,
            "schedule_days": [
                _schedule_day_payload(day)
                for day in sorted(default_schedule.days.all(), key=lambda item: item.weekday)
                if day.weekday in relevant_weekdays
            ]
            if default_schedule
            else [],
            "approved_leaves": [
                _leave_payload(leave)
                for leave in employee.leaves.all()
                if leave.status == EmployeeLeave.Status.APPROVED and _date_ranges_overlap(
                    leave.start_date,
                    leave.end_date,
                    window_start,
                    window_end,
                )
            ],
            "availability_overrides": [
                _availability_override_payload(override)
                for override in employee.availability_overrides.all()
                if window_start <= override.date <= window_end
            ],
        },
    }


def _get_assignment_case_queryset(changed_since: datetime | None) -> QuerySet[Assignment]:
    """Select assignments that can affect the derived `assignment_case` retrieval corpus."""

    queryset = (
        Assignment.objects.select_related(
            "task__department",
            "employee__department",
        )
        .prefetch_related(
            Prefetch(
                "task__requirements",
                queryset=TaskRequirement.objects.select_related("skill").order_by("id"),
            ),
            Prefetch(
                "employee__skills",
                queryset=EmployeeSkill.objects.select_related("skill").order_by("id"),
            ),
            "change_log",
        )
        .filter(status__in=AI_SUCCESS_ASSIGNMENT_STATUSES | AI_DELETE_ASSIGNMENT_STATUSES)
        .order_by("id")
    )
    if changed_since is None:
        return queryset

    return queryset.filter(
        Q(approved_at__gt=changed_since)
        | Q(assigned_at__gt=changed_since)
        | Q(change_log__created_at__gt=changed_since)
        | Q(task__updated_at__gt=changed_since)
        | Q(employee__updated_at__gt=changed_since)
        | Q(task__department__updated_at__gt=changed_since)
        | Q(employee__department__updated_at__gt=changed_since)
        | Q(task__requirements__skill__updated_at__gt=changed_since)
        | Q(employee__skills__updated_at__gt=changed_since)
        | Q(employee__skills__skill__updated_at__gt=changed_since)
    ).distinct()


def _get_task_for_ai_context(task_id: int) -> Task:
    """Load one task together with the requirement payload needed by ai-layer."""

    return (
        Task.objects.select_related("department")
        .prefetch_related(
            Prefetch(
                "requirements",
                queryset=TaskRequirement.objects.select_related("skill").order_by("id"),
            )
        )
        .get(pk=task_id)
    )


def _get_employee_for_ai_context(employee_id: int) -> Employee:
    """Load one employee together with the live availability slice dependencies."""

    return (
        Employee.objects.select_related("department")
        .prefetch_related(
            Prefetch(
                "skills",
                queryset=EmployeeSkill.objects.select_related("skill").order_by("id"),
            ),
            Prefetch(
                "schedules",
                queryset=WorkSchedule.objects.prefetch_related(
                    Prefetch("days", queryset=WorkScheduleDay.objects.order_by("weekday"))
                ).order_by("id"),
            ),
            Prefetch("leaves", queryset=EmployeeLeave.objects.order_by("start_date", "id")),
            Prefetch(
                "availability_overrides",
                queryset=EmployeeAvailabilityOverride.objects.order_by("date", "id"),
            ),
        )
        .get(pk=employee_id)
    )


def _assignment_source_updated_at(assignment: Assignment) -> datetime:
    """Compute the current flattened-source freshness timestamp for one assignment case."""

    timestamps = [
        assignment.assigned_at,
        assignment.approved_at,
        assignment.task.updated_at,
        assignment.employee.updated_at,
    ]
    if assignment.task.department_id and assignment.task.department is not None:
        timestamps.append(assignment.task.department.updated_at)
    if assignment.employee.department_id and assignment.employee.department is not None:
        timestamps.append(assignment.employee.department.updated_at)
    timestamps.extend(change.created_at for change in assignment.change_log.all())
    timestamps.extend(skill.updated_at for skill in assignment.employee.skills.all())
    timestamps.extend(
        skill.skill.updated_at
        for skill in assignment.employee.skills.all()
        if hasattr(skill.skill, "updated_at")
    )
    timestamps.extend(
        requirement.skill.updated_at
        for requirement in assignment.task.requirements.all()
        if hasattr(requirement.skill, "updated_at")
    )
    return max(timestamp for timestamp in timestamps if timestamp is not None)


def _assignment_index_action(assignment: Assignment) -> str:
    """Map the current assignment status to the sync action expected by ai-layer."""

    if assignment.status in AI_DELETE_ASSIGNMENT_STATUSES:
        return "delete"
    return "upsert"


def _assignment_case_title(assignment: Assignment) -> str:
    """Build a short retrieval title for one assignment case."""

    return f"{assignment.task.title} -> {assignment.employee.full_name}"


def _assignment_case_content(assignment: Assignment) -> str:
    """Build a flattened retrieval body for one assignment case."""

    requirement_lines = [
        f"- {requirement.skill.name}: min_level={requirement.min_level}, weight={float(requirement.weight):.2f}"
        for requirement in assignment.task.requirements.all()
    ]
    skill_lines = [
        f"- {skill.skill.name}: level={skill.level}"
        for skill in assignment.employee.skills.all()
    ]
    return "\n".join(
        [
            f"Task: {assignment.task.title}",
            f"Task description: {assignment.task.description or 'n/a'}",
            f"Task priority/status: {assignment.task.priority} / {assignment.task.status}",
            f"Task department: {assignment.task.department.name if assignment.task.department else 'n/a'}",
            f"Task window: {(assignment.task.start_date or assignment.task.due_date).isoformat()} -> {assignment.task.due_date.isoformat()}",
            f"Task estimated hours: {assignment.task.estimated_hours}",
            "Task requirements:",
            *(requirement_lines or ["- none"]),
            f"Employee: {assignment.employee.full_name} ({assignment.employee.position_name})",
            f"Employee department/timezone: {assignment.employee.department.name if assignment.employee.department else 'n/a'} / {assignment.employee.timezone}",
            "Employee skills:",
            *(skill_lines or ["- none"]),
            f"Assignment status/source: {assignment.status} / {assignment.assigned_by_type}",
            f"Assignment planned hours: {assignment.planned_hours}",
            f"Assignment notes: {assignment.notes or 'n/a'}",
            f"Source plan run id: {assignment.source_plan_run_id or 'manual'}",
        ]
    )


def _assignment_case_metadata(assignment: Assignment) -> dict[str, Any]:
    """Build the structured metadata stored alongside one assignment case."""

    return {
        "assignment_id": str(assignment.id),
        "task_id": str(assignment.task_id),
        "task_status": assignment.task.status,
        "task_priority": assignment.task.priority,
        "department_id": str(assignment.task.department_id) if assignment.task.department_id else None,
        "employee_id": str(assignment.employee_id),
        "employee_department_id": str(assignment.employee.department_id) if assignment.employee.department_id else None,
        "assignment_status": assignment.status,
        "assigned_by_type": assignment.assigned_by_type,
        "planned_hours": assignment.planned_hours,
        "source_plan_run_id": str(assignment.source_plan_run_id) if assignment.source_plan_run_id else None,
        "requirements": [_requirement_payload(requirement) for requirement in assignment.task.requirements.all()],
        "employee_skills": [_employee_skill_payload(skill) for skill in assignment.employee.skills.all()],
    }


def _requirement_payload(requirement: TaskRequirement) -> dict[str, Any]:
    """Serialize one task requirement into the internal AI payload shape."""

    return {
        "skill_id": str(requirement.skill_id),
        "skill_name": requirement.skill.name,
        "min_level": requirement.min_level,
        "weight": float(requirement.weight),
    }


def _employee_skill_payload(skill: EmployeeSkill) -> dict[str, Any]:
    """Serialize one employee skill into the internal AI payload shape."""

    return {
        "skill_id": str(skill.skill_id),
        "skill_name": skill.skill.name,
        "level": skill.level,
    }


def _schedule_day_payload(day: WorkScheduleDay) -> dict[str, Any]:
    """Serialize one default schedule weekday rule for live context."""

    return {
        "weekday": day.weekday,
        "is_working_day": day.is_working_day,
        "capacity_hours": day.capacity_hours,
        "start_time": day.start_time.isoformat() if day.start_time else None,
        "end_time": day.end_time.isoformat() if day.end_time else None,
    }


def _leave_payload(leave: EmployeeLeave) -> dict[str, Any]:
    """Serialize one leave record that intersects the task window."""

    return {
        "id": str(leave.id),
        "leave_type": leave.leave_type,
        "status": leave.status,
        "start_date": leave.start_date.isoformat(),
        "end_date": leave.end_date.isoformat(),
        "comment": leave.comment,
    }


def _availability_override_payload(override: EmployeeAvailabilityOverride) -> dict[str, Any]:
    """Serialize one availability override that intersects the task window."""

    return {
        "id": str(override.id),
        "date": override.date.isoformat(),
        "available_hours": override.available_hours,
        "reason": override.reason,
        "created_at": override.created_at.isoformat(),
    }


def _task_window(task: Task) -> tuple[date, date]:
    """Return the inclusive date window that matters for a date-based task."""

    return task.start_date or task.due_date, task.due_date


def _window_weekdays(window_start: date, window_end: date) -> set[int]:
    """Return the set of weekdays that appear in the task window."""

    weekdays: set[int] = set()
    for current_date in _date_range(window_start, window_end):
        weekdays.add(current_date.weekday())
    return weekdays


def _get_default_schedule(employee: Employee) -> WorkSchedule | None:
    """Choose the employee default schedule or the first deterministic fallback."""

    schedules = list(employee.schedules.all())
    for schedule in schedules:
        if schedule.is_default:
            return schedule
    return schedules[0] if schedules else None


def _date_range(start_date: date, end_date: date):
    """Yield every date inside one inclusive date interval."""

    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def _date_ranges_overlap(
    left_start: date,
    left_end: date,
    right_start: date,
    right_end: date,
) -> bool:
    """Return whether two inclusive date ranges overlap at least one day."""

    return left_start <= right_end and right_start <= left_end
