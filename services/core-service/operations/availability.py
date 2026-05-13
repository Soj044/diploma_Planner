"""Shared availability resolution for planner snapshots and schedule previews.

This module keeps one backend-owned interpretation of weekly schedules,
approved leaves, and availability overrides so frontend previews and planner
snapshots do not diverge.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from contracts.schemas import EmployeeAvailability

from .models import Employee, EmployeeAvailabilityOverride, EmployeeLeave, WorkSchedule, WorkScheduleDay

DEFAULT_SLOT_START = time.min
WEEKDAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass(frozen=True)
class ResolvedScheduleDate:
    """Effective employee availability for one concrete calendar date."""

    current_date: date
    weekday: int
    weekday_label: str
    base_rule: WorkScheduleDay | None
    approved_leave: EmployeeLeave | None
    availability_override: EmployeeAvailabilityOverride | None
    source: str
    is_working_day: bool
    capacity_hours: int
    start_time: time | None
    end_time: time | None

    def to_employee_availability(self) -> EmployeeAvailability | None:
        """Return a planner slot for the effective date, or None when unavailable."""

        if not self.is_working_day or self.capacity_hours <= 0:
            return None

        start_at = datetime.combine(self.current_date, self.start_time or DEFAULT_SLOT_START, tzinfo=timezone.utc)
        end_at = (
            datetime.combine(self.current_date, self.end_time, tzinfo=timezone.utc)
            if self.end_time
            else next_day_start(self.current_date)
        )
        return EmployeeAvailability(start_at=start_at, end_at=end_at, available_hours=self.capacity_hours)

    def to_preview_payload(self) -> dict[str, Any]:
        """Serialize one effective date into the schedule preview read model."""

        return {
            "date": self.current_date.isoformat(),
            "weekday": self.weekday,
            "weekday_label": self.weekday_label,
            "base_rule": serialize_schedule_rule(self.base_rule),
            "effective_day": {
                "is_working_day": self.is_working_day,
                "capacity_hours": self.capacity_hours,
                "start_time": serialize_time(self.start_time),
                "end_time": serialize_time(self.end_time),
                "source": self.source,
            },
            "approved_leave": serialize_leave_summary(self.approved_leave),
            "availability_override": serialize_override_summary(self.availability_override),
        }


def build_employee_availability(
    employee: Employee,
    period_start: date,
    period_end: date,
    *,
    schedule: WorkSchedule | None = None,
) -> list[EmployeeAvailability]:
    """Build planner slots from effective day resolution for the requested period."""

    resolved_days = resolve_schedule_window(employee, period_start, period_end, schedule=schedule)
    return [slot for slot in (resolved_day.to_employee_availability() for resolved_day in resolved_days) if slot is not None]


def build_schedule_week_preview(
    employee: Employee,
    week_start: date,
    *,
    schedule: WorkSchedule | None = None,
) -> dict[str, Any]:
    """Build one Monday-based seven-day preview for the selected employee schedule."""

    normalized_week_start = normalize_week_start(week_start)
    week_end = normalized_week_start + timedelta(days=6)
    selected_schedule = schedule or get_default_schedule(employee)
    resolved_days = resolve_schedule_window(employee, normalized_week_start, week_end, schedule=selected_schedule)

    return {
        "employee": {
            "id": employee.id,
            "full_name": employee.full_name,
            "position_name": employee.position_name,
            "department_id": employee.department_id,
            "department_name": employee.department.name if employee.department_id else None,
        },
        "schedule": (
            {
                "id": selected_schedule.id,
                "name": selected_schedule.name,
                "is_default": selected_schedule.is_default,
            }
            if selected_schedule
            else None
        ),
        "week_start": normalized_week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "days": [resolved_day.to_preview_payload() for resolved_day in resolved_days],
    }


def resolve_schedule_window(
    employee: Employee,
    period_start: date,
    period_end: date,
    *,
    schedule: WorkSchedule | None = None,
) -> list[ResolvedScheduleDate]:
    """Resolve effective schedule state for each date in the inclusive range."""

    selected_schedule = schedule or get_default_schedule(employee)
    leave_by_date = approved_leave_map(employee, period_start, period_end)
    overrides_by_date = {override.date: override for override in employee.availability_overrides.all()}

    return [
        resolve_schedule_date(
            current_date=current_date,
            schedule=selected_schedule,
            leave_by_date=leave_by_date,
            overrides_by_date=overrides_by_date,
        )
        for current_date in daterange(period_start, period_end)
    ]


def resolve_schedule_date(
    *,
    current_date: date,
    schedule: WorkSchedule | None,
    leave_by_date: dict[date, EmployeeLeave],
    overrides_by_date: dict[date, EmployeeAvailabilityOverride],
) -> ResolvedScheduleDate:
    """Resolve one calendar date with leave and override precedence."""

    base_rule = get_schedule_day(schedule, current_date.weekday())
    approved_leave = leave_by_date.get(current_date)
    availability_override = overrides_by_date.get(current_date)

    if approved_leave is not None:
        return ResolvedScheduleDate(
            current_date=current_date,
            weekday=current_date.weekday(),
            weekday_label=WEEKDAY_LABELS[current_date.weekday()],
            base_rule=base_rule,
            approved_leave=approved_leave,
            availability_override=availability_override,
            source="approved_leave",
            is_working_day=False,
            capacity_hours=0,
            start_time=None,
            end_time=None,
        )

    if availability_override is not None:
        return ResolvedScheduleDate(
            current_date=current_date,
            weekday=current_date.weekday(),
            weekday_label=WEEKDAY_LABELS[current_date.weekday()],
            base_rule=base_rule,
            approved_leave=None,
            availability_override=availability_override,
            source="availability_override",
            is_working_day=availability_override.available_hours > 0,
            capacity_hours=max(int(availability_override.available_hours), 0),
            start_time=base_rule.start_time if base_rule else None,
            end_time=base_rule.end_time if base_rule else None,
        )

    if base_rule is None:
        return ResolvedScheduleDate(
            current_date=current_date,
            weekday=current_date.weekday(),
            weekday_label=WEEKDAY_LABELS[current_date.weekday()],
            base_rule=None,
            approved_leave=None,
            availability_override=None,
            source="no_rule",
            is_working_day=False,
            capacity_hours=0,
            start_time=None,
            end_time=None,
        )

    return ResolvedScheduleDate(
        current_date=current_date,
        weekday=current_date.weekday(),
        weekday_label=WEEKDAY_LABELS[current_date.weekday()],
        base_rule=base_rule,
        approved_leave=None,
        availability_override=None,
        source="schedule",
        is_working_day=base_rule.is_working_day and base_rule.capacity_hours > 0,
        capacity_hours=base_rule.capacity_hours if base_rule.is_working_day else 0,
        start_time=base_rule.start_time,
        end_time=base_rule.end_time,
    )


def normalize_week_start(value: date) -> date:
    """Normalize any date to the Monday that starts its week."""

    return value - timedelta(days=value.weekday())


def daterange(period_start: date, period_end: date):
    """Yield every date in the inclusive range."""

    day_count = (period_end - period_start).days + 1
    for offset in range(day_count):
        yield period_start + timedelta(days=offset)


def next_day_start(current_date: date) -> datetime:
    """Return the exclusive upper boundary for one calendar day."""

    return datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=timezone.utc)


def get_default_schedule(employee: Employee) -> WorkSchedule | None:
    """Choose the default schedule or a deterministic fallback."""

    schedules = sorted(employee.schedules.all(), key=lambda schedule: schedule.id)
    for schedule in schedules:
        if schedule.is_default:
            return schedule
    return schedules[0] if schedules else None


def get_schedule_day(schedule: WorkSchedule | None, weekday: int) -> WorkScheduleDay | None:
    """Return the stored weekly rule for the requested weekday."""

    if schedule is None:
        return None
    for day in schedule.days.all():
        if day.weekday == weekday:
            return day
    return None


def approved_leave_map(employee: Employee, period_start: date, period_end: date) -> dict[date, EmployeeLeave]:
    """Expand approved leave periods into a date map used by previews and snapshots."""

    leaves = sorted(
        (leave for leave in employee.leaves.all() if leave.status == EmployeeLeave.Status.APPROVED),
        key=lambda leave: (leave.start_date, leave.id),
    )
    mapped_dates: dict[date, EmployeeLeave] = {}
    for leave in leaves:
        current_start = max(period_start, leave.start_date)
        current_end = min(period_end, leave.end_date)
        if current_start > current_end:
            continue
        for current_date in daterange(current_start, current_end):
            mapped_dates.setdefault(current_date, leave)
    return mapped_dates


def serialize_schedule_rule(rule: WorkScheduleDay | None) -> dict[str, Any] | None:
    """Serialize the stored weekly rule for one preview day."""

    if rule is None:
        return None
    return {
        "is_working_day": rule.is_working_day,
        "capacity_hours": rule.capacity_hours,
        "start_time": serialize_time(rule.start_time),
        "end_time": serialize_time(rule.end_time),
    }


def serialize_leave_summary(leave: EmployeeLeave | None) -> dict[str, Any] | None:
    """Serialize one leave overlap for preview rendering."""

    if leave is None:
        return None
    return {
        "id": leave.id,
        "leave_type": leave.leave_type,
        "start_date": leave.start_date.isoformat(),
        "end_date": leave.end_date.isoformat(),
    }


def serialize_override_summary(override: EmployeeAvailabilityOverride | None) -> dict[str, Any] | None:
    """Serialize one availability override overlap for preview rendering."""

    if override is None:
        return None
    return {
        "id": override.id,
        "date": override.date.isoformat(),
        "available_hours": override.available_hours,
        "reason": override.reason,
    }


def serialize_time(value: time | None) -> str | None:
    """Serialize time values in the same format as DRF time fields."""

    return value.isoformat() if value is not None else None
