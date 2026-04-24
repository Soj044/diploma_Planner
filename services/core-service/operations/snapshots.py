"""Helpers for exporting planning snapshots from core-service truth."""

from datetime import date, datetime, time, timedelta, timezone

from django.db.models import Q

from contracts.schemas import (
    CreatePlanRunRequest,
    EmployeeAvailability,
    EmployeeSnapshot,
    PlanningSnapshot,
    SkillRequirement,
    TaskSnapshot,
)

from .models import Assignment, Employee, EmployeeLeave, Task, WorkSchedule

DEFAULT_SLOT_START = time.min


def build_planning_snapshot(request: CreatePlanRunRequest) -> PlanningSnapshot:
    """Build a planner-ready snapshot from current core data."""

    tasks = list(_get_tasks(request))
    employees = list(_get_employees(request))
    task_snapshots = [_build_task_snapshot(task) for task in tasks]
    employee_snapshots = [
        _build_employee_snapshot(employee, request.planning_period_start, request.planning_period_end)
        for employee in employees
    ]

    period_start = datetime.combine(request.planning_period_start, time.min, tzinfo=timezone.utc)
    requested_period_end = _next_day_start(request.planning_period_end)
    latest_task_end = max((task.ends_at for task in task_snapshots), default=requested_period_end)

    return PlanningSnapshot(
        planning_period_start=period_start,
        planning_period_end=max(requested_period_end, latest_task_end),
        employees=employee_snapshots,
        tasks=task_snapshots,
    )


def _get_tasks(request: CreatePlanRunRequest):
    """Select planner-visible tasks that still need assignment in the requested window."""

    tasks = (
        Task.objects.select_related("department", "created_by_user")
        .prefetch_related("requirements")
        .filter(status=Task.Status.PLANNED)
        .exclude(assignments__status__in=[Assignment.Status.APPROVED, Assignment.Status.ACTIVE, Assignment.Status.COMPLETED])
        .filter(due_date__gte=request.planning_period_start, due_date__lte=request.planning_period_end)
        .filter(Q(start_date__isnull=True) | Q(start_date__gte=request.planning_period_start))
        .distinct()
        .order_by("id")
    )
    if request.department_id:
        tasks = tasks.filter(department_id=request.department_id)
    if request.task_ids:
        tasks = tasks.filter(id__in=request.task_ids)
    return tasks


def _get_employees(request: CreatePlanRunRequest):
    """Select active employees and prefetch the data needed to build planner availability."""

    employees = (
        Employee.objects.select_related("department")
        .prefetch_related(
            "skills__skill",
            "schedules__days",
            "leaves",
            "availability_overrides",
        )
        .filter(is_active=True)
        .order_by("id")
    )
    if request.department_id:
        employees = employees.filter(department_id=request.department_id)
    return employees


def _build_task_snapshot(task: Task) -> TaskSnapshot:
    """Translate a core task into the normalized planner task shape."""

    starts_at = datetime.combine(task.start_date or task.due_date, DEFAULT_SLOT_START, tzinfo=timezone.utc)
    ends_at = _next_day_start(task.due_date)
    return TaskSnapshot(
        task_id=str(task.id),
        department_id=str(task.department_id) if task.department_id else None,
        title=task.title,
        starts_at=starts_at,
        ends_at=ends_at,
        estimated_hours=task.estimated_hours,
        requirements=[
            SkillRequirement(
                skill_id=str(requirement.skill_id),
                min_level=requirement.min_level,
                weight=float(requirement.weight),
            )
            for requirement in task.requirements.all()
        ],
    )


def _build_employee_snapshot(
    employee: Employee,
    period_start: date,
    period_end: date,
) -> EmployeeSnapshot:
    """Build employee availability slots for the planning window from schedules and overrides."""

    availability = []
    default_schedule = _get_default_schedule(employee)
    leave_dates = _leave_dates(employee, period_start, period_end)
    overrides = {override.date: override for override in employee.availability_overrides.all()}

    for current_date in _daterange(period_start, period_end):
        if current_date in leave_dates:
            continue

        override = overrides.get(current_date)
        if override is not None:
            if override.available_hours <= 0:
                continue
            # A daily override replaces the default schedule capacity for that date.
            availability.append(_build_override_slot(default_schedule, current_date, override.available_hours))
            continue

        schedule_day = _get_schedule_day(default_schedule, current_date.weekday())
        if schedule_day is None or not schedule_day.is_working_day or schedule_day.capacity_hours <= 0:
            continue

        start_at = datetime.combine(current_date, schedule_day.start_time or DEFAULT_SLOT_START, tzinfo=timezone.utc)
        end_at = (
            datetime.combine(current_date, schedule_day.end_time, tzinfo=timezone.utc)
            if schedule_day.end_time
            else _next_day_start(current_date)
        )
        availability.append(
            EmployeeAvailability(
                start_at=start_at,
                end_at=end_at,
                available_hours=schedule_day.capacity_hours,
            )
        )

    return EmployeeSnapshot(
        employee_id=str(employee.id),
        department_id=str(employee.department_id) if employee.department_id else None,
        is_active=employee.is_active,
        skill_levels={str(skill.skill_id): skill.level for skill in employee.skills.all()},
        availability=availability,
    )


def _build_override_slot(schedule: WorkSchedule | None, current_date: date, available_hours: int) -> EmployeeAvailability:
    """Turn an availability override into a planner slot with schedule-aligned boundaries."""

    schedule_day = _get_schedule_day(schedule, current_date.weekday())
    start_at = datetime.combine(
        current_date,
        schedule_day.start_time if schedule_day and schedule_day.start_time else DEFAULT_SLOT_START,
        tzinfo=timezone.utc,
    )
    end_at = (
        datetime.combine(current_date, schedule_day.end_time, tzinfo=timezone.utc)
        if schedule_day and schedule_day.end_time
        else _next_day_start(current_date)
    )
    return EmployeeAvailability(start_at=start_at, end_at=end_at, available_hours=available_hours)


def _daterange(period_start: date, period_end: date):
    """Yield every date in the inclusive planning range."""

    day_count = (period_end - period_start).days + 1
    for offset in range(day_count):
        yield period_start + timedelta(days=offset)


def _get_default_schedule(employee: Employee) -> WorkSchedule | None:
    """Choose the employee's default schedule or a deterministic fallback."""

    schedules = sorted(employee.schedules.all(), key=lambda schedule: schedule.id)
    for schedule in schedules:
        if schedule.is_default:
            return schedule
    return schedules[0] if schedules else None


def _get_schedule_day(schedule: WorkSchedule | None, weekday: int):
    """Return the schedule rule that applies to a concrete weekday."""

    if schedule is None:
        return None
    for day in schedule.days.all():
        if day.weekday == weekday:
            return day
    return None


def _leave_dates(employee: Employee, period_start: date, period_end: date) -> set[date]:
    """Expand approved leave periods into concrete dates excluded from planning."""

    dates: set[date] = set()
    for leave in employee.leaves.all():
        if leave.status != EmployeeLeave.Status.APPROVED:
            continue
        current_start = max(period_start, leave.start_date)
        current_end = min(period_end, leave.end_date)
        if current_start > current_end:
            continue
        dates.update(_daterange(current_start, current_end))
    return dates


def _next_day_start(current_date: date) -> datetime:
    """Return the exclusive upper boundary for a date-based planning interval."""

    return datetime.combine(current_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
