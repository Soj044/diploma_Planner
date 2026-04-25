"""API routes for core-service MVP."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AssignmentChangeLogViewSet,
    AssignmentViewSet,
    DepartmentViewSet,
    EmployeeAvailabilityOverrideViewSet,
    EmployeeLeaveViewSet,
    EmployeeSkillViewSet,
    EmployeeViewSet,
    SkillViewSet,
    TaskRequirementViewSet,
    TaskViewSet,
    PlanningSnapshotView,
    WorkScheduleDayViewSet,
    WorkScheduleViewSet,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet)
router.register("skills", SkillViewSet)
router.register("employees", EmployeeViewSet)
router.register("employee-skills", EmployeeSkillViewSet)
router.register("work-schedules", WorkScheduleViewSet)
router.register("work-schedule-days", WorkScheduleDayViewSet)
router.register("employee-leaves", EmployeeLeaveViewSet)
router.register("availability-overrides", EmployeeAvailabilityOverrideViewSet)
router.register("tasks", TaskViewSet)
router.register("task-requirements", TaskRequirementViewSet)
router.register("assignments", AssignmentViewSet)
router.register("assignment-change-logs", AssignmentChangeLogViewSet)

urlpatterns = [
    path("planning-snapshot/", PlanningSnapshotView.as_view(), name="planning-snapshot"),
    *router.urls,
]
