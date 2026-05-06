"""Маршруты core-service для CRUD, planner boundary и internal AI helper routes.

Этот файл связывает DRF viewsets и специальные endpoints в единый API surface
core-service. Через него доступны CRUD операций по задачам и assignments, а
также snapshot boundary для planner-service и token-protected internal AI
helper endpoints.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .ai_views import InternalAiServiceBoundaryView
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
    path(
        "internal/ai/service-boundary/",
        InternalAiServiceBoundaryView.as_view(),
        name="internal-ai-service-boundary",
    ),
    path("planning-snapshot/", PlanningSnapshotView.as_view(), name="planning-snapshot"),
    *router.urls,
]
