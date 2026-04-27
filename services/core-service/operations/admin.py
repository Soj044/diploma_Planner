"""Admin registrations for core-service business models."""

from django.contrib import admin

from .models import (
    Assignment,
    AssignmentChangeLog,
    Department,
    Employee,
    EmployeeAvailabilityOverride,
    EmployeeLeave,
    EmployeeSkill,
    Skill,
    Task,
    TaskRequirement,
    WorkSchedule,
    WorkScheduleDay,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "department", "position_name", "employment_type", "is_active")
    list_filter = ("employment_type", "is_active", "department")
    search_fields = ("full_name", "position_name", "user__email")


@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ("employee", "skill", "level")
    list_filter = ("skill",)
    search_fields = ("employee__full_name", "skill__name")


@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "employee", "is_default")
    list_filter = ("is_default",)
    search_fields = ("name", "employee__full_name")


@admin.register(WorkScheduleDay)
class WorkScheduleDayAdmin(admin.ModelAdmin):
    list_display = ("schedule", "weekday", "is_working_day", "capacity_hours")
    list_filter = ("weekday", "is_working_day")


@admin.register(EmployeeLeave)
class EmployeeLeaveAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "status", "start_date", "end_date")
    list_filter = ("leave_type", "status")
    search_fields = ("employee__full_name",)


@admin.register(EmployeeAvailabilityOverride)
class EmployeeAvailabilityOverrideAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "available_hours", "created_by_user")
    search_fields = ("employee__full_name", "created_by_user__email")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "status", "priority", "due_date", "estimated_hours")
    list_filter = ("status", "priority", "department")
    search_fields = ("title", "description")


@admin.register(TaskRequirement)
class TaskRequirementAdmin(admin.ModelAdmin):
    list_display = ("task", "skill", "min_level", "weight")
    list_filter = ("skill",)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("task", "employee", "status", "planned_hours", "start_date", "end_date")
    list_filter = ("status", "assigned_by_type")
    search_fields = ("task__title", "employee__full_name")


@admin.register(AssignmentChangeLog)
class AssignmentChangeLogAdmin(admin.ModelAdmin):
    list_display = ("assignment", "old_employee", "new_employee", "changed_by_user", "created_at")
    search_fields = ("assignment__task__title", "change_reason", "changed_by_user__email")
