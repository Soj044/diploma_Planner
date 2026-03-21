"""Admin registrations for core domain models."""

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

admin.site.register(Department)
admin.site.register(Skill)
admin.site.register(Employee)
admin.site.register(EmployeeSkill)
admin.site.register(WorkSchedule)
admin.site.register(WorkScheduleDay)
admin.site.register(EmployeeLeave)
admin.site.register(EmployeeAvailabilityOverride)
admin.site.register(Task)
admin.site.register(TaskRequirement)
admin.site.register(Assignment)
admin.site.register(AssignmentChangeLog)
