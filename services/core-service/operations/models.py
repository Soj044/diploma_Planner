"""Основные бизнес-сущности core-service для задач и назначений.

Этот файл хранит source of truth для сотрудников, навыков, графиков, задач,
требований и финальных assignments. На эти модели опираются serializers, views,
snapshot export в planner-service и approval handoff из planner proposals.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Base model for mutable business records."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Department(TimeStampedModel):
    """Enterprise unit used to group employees and tasks."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Skill(TimeStampedModel):
    """Skill catalog entry used by employees and task requirements."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Employee(TimeStampedModel):
    """Employee profile and planning capacity metadata."""

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full time"
        PART_TIME = "part_time", "Part time"
        CONTRACT = "contract", "Contract"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="employee_profile",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=255)
    position_name = models.CharField(max_length=255)
    employment_type = models.CharField(
        max_length=16,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
    )
    weekly_capacity_hours = models.PositiveSmallIntegerField(default=40)
    timezone = models.CharField(max_length=64, default="UTC")
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.full_name


class EmployeeSkill(TimeStampedModel):
    """Skill level owned by a specific employee."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="skills"
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="employees")
    level = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("employee", "skill"), name="unique_employee_skill"
            ),
            models.CheckConstraint(
                condition=models.Q(level__gte=1, level__lte=5),
                name="employee_skill_level_1_5",
            ),
        ]
        indexes = [
            models.Index(fields=("employee",), name="employee_skill_employee_idx"),
            models.Index(fields=("skill",), name="employee_skill_skill_idx"),
        ]

    def save(self, *args, **kwargs) -> None:
        """Persist the skill row and touch the parent employee for AI incremental sync."""

        super().save(*args, **kwargs)
        Employee.objects.filter(pk=self.employee_id).update(updated_at=timezone.now())

    def delete(self, *args, **kwargs):
        """Delete the skill row and touch the parent employee for AI incremental sync."""

        employee_id = self.employee_id
        deleted = super().delete(*args, **kwargs)
        Employee.objects.filter(pk=employee_id).update(updated_at=timezone.now())
        return deleted


class WorkSchedule(TimeStampedModel):
    """Reusable weekly schedule template for an employee."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="schedules"
    )
    name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.employee}: {self.name}"


class WorkScheduleDay(models.Model):
    """Capacity rule for one weekday in a schedule."""

    schedule = models.ForeignKey(
        WorkSchedule, on_delete=models.CASCADE, related_name="days"
    )
    weekday = models.PositiveSmallIntegerField()
    is_working_day = models.BooleanField(default=True)
    capacity_hours = models.PositiveSmallIntegerField(default=8)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("schedule", "weekday"), name="unique_schedule_weekday"
            ),
            models.CheckConstraint(
                condition=models.Q(weekday__gte=0, weekday__lte=6),
                name="schedule_weekday_0_6",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity_hours__lte=24),
                name="schedule_capacity_lte_24",
            ),
        ]
        indexes = [
            models.Index(fields=("schedule",), name="schedule_day_schedule_idx"),
        ]


class EmployeeLeave(TimeStampedModel):
    """Approved or requested employee absence period."""

    class LeaveType(models.TextChoices):
        VACATION = "vacation", "Vacation"
        SICK_LEAVE = "sick_leave", "Sick leave"
        DAY_OFF = "day_off", "Day off"
        BUSINESS_TRIP = "business_trip", "Business trip"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leaves"
    )
    leave_type = models.CharField(max_length=24, choices=LeaveType.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.APPROVED
    )
    start_date = models.DateField()
    end_date = models.DateField()
    comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lte=models.F("end_date")),
                name="leave_valid_period",
            ),
        ]
        indexes = [
            models.Index(fields=("employee",), name="employee_leave_employee_idx"),
            models.Index(
                fields=("employee", "start_date", "end_date"),
                name="employee_leave_period_idx",
            ),
        ]


class EmployeeAvailabilityOverride(models.Model):
    """Single-day availability override for an employee."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="availability_overrides"
    )
    date = models.DateField()
    available_hours = models.PositiveSmallIntegerField()
    reason = models.TextField(blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_availability_overrides",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("employee", "date"), name="unique_employee_override_date"
            ),
            models.CheckConstraint(
                condition=models.Q(available_hours__lte=24),
                name="override_hours_lte_24",
            ),
        ]
        indexes = [
            models.Index(fields=("employee",), name="availability_employee_idx"),
        ]


class Task(TimeStampedModel):
    """Business task that may keep a manual estimate and later store actual effort."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PLANNED = "planned", "Planned"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="tasks",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.MEDIUM
    )
    estimated_hours = models.PositiveSmallIntegerField(null=True, blank=True)
    actual_hours = models.PositiveSmallIntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__isnull=True)
                | models.Q(start_date__lte=models.F("due_date")),
                name="task_valid_period",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="done", actual_hours__gt=0)
                    | (~models.Q(status="done") & models.Q(actual_hours__isnull=True))
                ),
                name="task_actual_hours_match_done_status",
            ),
        ]
        indexes = [
            models.Index(fields=("status",), name="task_status_idx"),
            models.Index(fields=("priority",), name="task_priority_idx"),
            models.Index(fields=("due_date",), name="task_due_date_idx"),
            models.Index(fields=("department",), name="task_department_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class TaskRequirement(models.Model):
    """Skill requirement for a task."""

    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="requirements"
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.PROTECT, related_name="task_requirements"
    )
    min_level = models.PositiveSmallIntegerField(default=1)
    weight = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("1.00")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("task", "skill"), name="unique_task_requirement"
            ),
        ]
        indexes = [
            models.Index(fields=("task",), name="task_requirement_task_idx"),
            models.Index(fields=("skill",), name="task_requirement_skill_idx"),
        ]

    def save(self, *args, **kwargs) -> None:
        """Persist the requirement row and touch the parent task for AI incremental sync."""

        super().save(*args, **kwargs)
        Task.objects.filter(pk=self.task_id).update(updated_at=timezone.now())

    def delete(self, *args, **kwargs):
        """Delete the requirement row and touch the parent task for AI incremental sync."""

        task_id = self.task_id
        deleted = super().delete(*args, **kwargs)
        Task.objects.filter(pk=task_id).update(updated_at=timezone.now())
        return deleted


class Assignment(models.Model):
    """Final task assignment stored by core-service."""

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REJECTED = "rejected", "Rejected"

    class SourceType(models.TextChoices):
        SYSTEM = "system", "System"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Admin"

    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="assignments")
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="assignments"
    )
    source_plan_run_id = models.UUIDField(null=True, blank=True)
    planned_hours = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PROPOSED
    )
    assigned_by_type = models.CharField(
        max_length=16,
        choices=SourceType.choices,
        default=SourceType.SYSTEM,
    )
    assigned_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_assignments",
        null=True,
        blank=True,
    )
    approved_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_assignments",
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lte=models.F("end_date")),
                name="assignment_valid_period",
            ),
        ]
        indexes = [
            models.Index(fields=("task",), name="assignment_task_idx"),
            models.Index(fields=("employee",), name="assignment_employee_idx"),
            models.Index(fields=("status",), name="assignment_status_idx"),
            models.Index(
                fields=("source_plan_run_id",), name="assignment_plan_run_idx"
            ),
        ]


class AssignmentChangeLog(models.Model):
    """Audit record for assignment reassignment or manual change."""

    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="change_log"
    )
    old_employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="old_assignment_changes",
        null=True,
        blank=True,
    )
    new_employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="new_assignment_changes",
        null=True,
        blank=True,
    )
    change_reason = models.TextField()
    changed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assignment_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=("assignment",), name="assign_change_assignment_idx"),
            models.Index(fields=("created_at",), name="assign_change_created_idx"),
        ]
