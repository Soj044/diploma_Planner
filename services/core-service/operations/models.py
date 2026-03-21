"""Core domain models used by planning MVP."""

from django.contrib.auth.models import User
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile", null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.full_name


class EmployeeSkill(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="employees")
    level = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ("employee", "skill")


class WorkSchedule(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="schedules")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)


class WorkScheduleDay(models.Model):
    schedule = models.ForeignKey(WorkSchedule, on_delete=models.CASCADE, related_name="days")
    weekday = models.PositiveSmallIntegerField()  # 0 Monday ... 6 Sunday
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_working = models.BooleanField(default=True)

    class Meta:
        unique_together = ("schedule", "weekday")


class EmployeeLeave(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)


class EmployeeAvailabilityOverride(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="availability_overrides")
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)


class Task(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        ASSIGNED = "assigned", "Assigned"

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)


class TaskRequirement(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="requirements")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="task_requirements")
    min_level = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ("task", "skill")


class Assignment(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="assignments")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="assignments")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.APPROVED)
    planner_run_id = models.CharField(max_length=64, blank=True)


class AssignmentChangeLog(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="change_log")
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
