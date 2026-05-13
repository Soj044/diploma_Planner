"""Сборка PlanningSnapshot из бизнес-истины core-service.

Этот файл превращает core модели задач, сотрудников, графиков и ограничений в
контрактный snapshot для planner-service. Он связывает source of truth из
models.py с planning pipeline и не создает второй источник данных.
"""

from datetime import date, datetime, time, timezone

from django.db.models import Q

from contracts.schemas import (
    CreatePlanRunRequest,
    EmployeeSnapshot,
    HistoricalTaskSummary,
    PlanningSnapshot,
    SkillRequirement,
    TaskSnapshot,
)

from .availability import build_employee_availability, next_day_start
from .models import Assignment, Employee, Task

DEFAULT_SLOT_START = time.min
HISTORICAL_TASK_LIMIT = 200


def build_planning_snapshot(request: CreatePlanRunRequest) -> PlanningSnapshot:
    """Build a planner-ready snapshot from current core data."""

    tasks = list(_get_tasks(request))
    employees = list(_get_employees(request))
    historical_tasks = list(_get_historical_tasks(request))
    task_snapshots = [_build_task_snapshot(task) for task in tasks]
    historical_task_summaries = [_build_historical_task_summary(task) for task in historical_tasks]
    employee_snapshots = [
        _build_employee_snapshot(employee, request.planning_period_start, request.planning_period_end)
        for employee in employees
    ]

    period_start = datetime.combine(request.planning_period_start, time.min, tzinfo=timezone.utc)
    requested_period_end = next_day_start(request.planning_period_end)
    latest_task_end = max((task.ends_at for task in task_snapshots), default=requested_period_end)

    return PlanningSnapshot(
        planning_period_start=period_start,
        planning_period_end=max(requested_period_end, latest_task_end),
        employees=employee_snapshots,
        tasks=task_snapshots,
        historical_tasks=historical_task_summaries,
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


def _get_historical_tasks(request: CreatePlanRunRequest):
    """Return a bounded slice of completed tasks with real actual-hours truth."""

    tasks = (
        Task.objects.select_related("department")
        .prefetch_related("requirements")
        .filter(status=Task.Status.DONE, actual_hours__isnull=False)
        .order_by("-updated_at", "-id")
    )
    if request.department_id:
        tasks = tasks.filter(department_id=request.department_id)
    return tasks[:HISTORICAL_TASK_LIMIT]


def _build_task_snapshot(task: Task) -> TaskSnapshot:
    """Translate a core task into the normalized planner task shape."""

    starts_at = datetime.combine(task.start_date or task.due_date, DEFAULT_SLOT_START, tzinfo=timezone.utc)
    ends_at = next_day_start(task.due_date)
    return TaskSnapshot(
        task_id=str(task.id),
        department_id=str(task.department_id) if task.department_id else None,
        title=task.title,
        priority=task.priority,
        starts_at=starts_at,
        ends_at=ends_at,
        estimated_hours=task.estimated_hours,
        requirements=_build_skill_requirements(task),
    )


def _build_historical_task_summary(task: Task) -> HistoricalTaskSummary:
    """Translate one completed task into the bounded history slice used by planner estimates."""

    return HistoricalTaskSummary(
        task_id=str(task.id),
        department_id=str(task.department_id) if task.department_id else None,
        priority=task.priority,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours or 0,
        requirements=_build_skill_requirements(task),
        start_date=task.start_date,
        due_date=task.due_date,
    )


def _build_skill_requirements(task: Task) -> list[SkillRequirement]:
    """Normalize task requirements so live tasks and historical tasks share one contract shape."""

    return [
        SkillRequirement(
            skill_id=str(requirement.skill_id),
            min_level=requirement.min_level,
            weight=float(requirement.weight),
        )
        for requirement in task.requirements.all()
    ]


def _build_employee_snapshot(
    employee: Employee,
    period_start: date,
    period_end: date,
) -> EmployeeSnapshot:
    """Build employee availability slots for the planning window from schedules and overrides."""

    return EmployeeSnapshot(
        employee_id=str(employee.id),
        department_id=str(employee.department_id) if employee.department_id else None,
        is_active=employee.is_active,
        skill_levels={str(skill.skill_id): skill.level for skill in employee.skills.all()},
        availability=build_employee_availability(employee, period_start, period_end),
    )
