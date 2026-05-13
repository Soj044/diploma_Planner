"""DRF endpoints core-service для задач, snapshot export и approval handoff.

Этот файл публикует CRUD API для основных сущностей, endpoint выгрузки
PlanningSnapshot в planner-service и endpoint утверждения выбранного proposal.
Он связывает serializers, snapshot builders и approval business logic.
"""

from contracts.schemas import CreatePlanRunRequest
from django.db.models import Prefetch
from pydantic import ValidationError as PydanticValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .availability import build_schedule_week_preview
from .approvals import reject_assignment
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
from .permissions import (
    AssignmentChangeLogPermission,
    AssignmentPermission,
    AvailabilityOverridePermission,
    DepartmentPermission,
    EmployeeLeavePermission,
    EmployeePermission,
    EmployeeSkillPermission,
    InternalPlannerServiceTokenPermission,
    PlannerApprovalPermission,
    SchedulePreviewPermission,
    SkillPermission,
    TaskPermission,
    TaskRequirementPermission,
    WorkScheduleDayPermission,
    WorkSchedulePermission,
)
from .planner_client import PlannerServiceError
from .snapshots import build_planning_snapshot
from .serializers import (
    AssignmentChangeLogSerializer,
    AssignmentApprovalSerializer,
    AssignmentManualCreateSerializer,
    AssignmentSerializer,
    DepartmentSerializer,
    EmployeeAvailabilityOverrideSerializer,
    EmployeeLeaveSerializer,
    EmployeeLeaveStatusSerializer,
    EmployeeSerializer,
    EmployeeSkillSerializer,
    SchedulePreviewQuerySerializer,
    SkillSerializer,
    TaskRequirementSerializer,
    TaskSerializer,
    WorkScheduleDaySerializer,
    WorkScheduleSerializer,
)


class PlanningSnapshotView(APIView):
    permission_classes = [InternalPlannerServiceTokenPermission]

    def post(self, request):
        try:
            payload = CreatePlanRunRequest.model_validate(request.data)
        except PydanticValidationError as exc:
            return Response({"detail": exc.errors()}, status=status.HTTP_400_BAD_REQUEST)

        snapshot = build_planning_snapshot(payload)
        return Response(snapshot.model_dump(mode="json"), status=status.HTTP_200_OK)


class SchedulePreviewView(APIView):
    permission_classes = [SchedulePreviewPermission]

    def get(self, request):
        serializer = SchedulePreviewQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        employee_id = serializer.validated_data["employee_id"]
        user_role = getattr(request.user, "role", "")
        if user_role == "employee":
            employee_profile = getattr(request.user, "employee_profile", None)
            if employee_profile is None:
                raise PermissionDenied("Employee profile is required.")
            if employee_profile.id != employee_id:
                raise PermissionDenied("You can only preview your own schedule.")

        employee = (
            Employee.objects.select_related("department")
            .prefetch_related("schedules__days", "leaves", "availability_overrides")
            .filter(id=employee_id)
            .first()
        )
        if employee is None:
            raise NotFound("Employee was not found.")

        selected_schedule = None
        schedule_id = serializer.validated_data.get("schedule_id")
        if schedule_id is not None:
            selected_schedule = next((schedule for schedule in employee.schedules.all() if schedule.id == schedule_id), None)
            if selected_schedule is None:
                raise ValidationError({"schedule_id": "schedule_id must belong to the requested employee."})

        preview = build_schedule_week_preview(
            employee=employee,
            week_start=serializer.validated_data["week_start"],
            schedule=selected_schedule,
        )
        return Response(preview, status=status.HTTP_200_OK)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by("id").prefetch_related(
        Prefetch("employees", queryset=Employee.objects.order_by("id"))
    )
    serializer_class = DepartmentSerializer
    permission_classes = [DepartmentPermission]


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all().order_by("id")
    serializer_class = SkillSerializer
    permission_classes = [SkillPermission]


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by("id")
    serializer_class = EmployeeSerializer
    permission_classes = [EmployeePermission]


class EmployeeSkillViewSet(viewsets.ModelViewSet):
    queryset = EmployeeSkill.objects.all().order_by("id")
    serializer_class = EmployeeSkillSerializer
    permission_classes = [EmployeeSkillPermission]


class WorkScheduleViewSet(viewsets.ModelViewSet):
    queryset = WorkSchedule.objects.all().order_by("id")
    serializer_class = WorkScheduleSerializer
    permission_classes = [WorkSchedulePermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self.request.user, "role", "") == "employee":
            employee_profile = getattr(self.request.user, "employee_profile", None)
            if employee_profile is None:
                return WorkSchedule.objects.none()
            return queryset.filter(employee_id=employee_profile.id)
        return queryset


class WorkScheduleDayViewSet(viewsets.ModelViewSet):
    queryset = WorkScheduleDay.objects.all().order_by("id")
    serializer_class = WorkScheduleDaySerializer
    permission_classes = [WorkScheduleDayPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self.request.user, "role", "") == "employee":
            employee_profile = getattr(self.request.user, "employee_profile", None)
            if employee_profile is None:
                return WorkScheduleDay.objects.none()
            return queryset.filter(schedule__employee_id=employee_profile.id)
        return queryset


class EmployeeLeaveViewSet(viewsets.ModelViewSet):
    queryset = EmployeeLeave.objects.all().order_by("id")
    serializer_class = EmployeeLeaveSerializer
    permission_classes = [EmployeeLeavePermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        user_role = getattr(self.request.user, "role", "")
        if user_role == "employee":
            employee_profile = getattr(self.request.user, "employee_profile", None)
            if employee_profile is None:
                return EmployeeLeave.objects.none()
            return queryset.filter(employee_id=employee_profile.id)
        if user_role in {"manager", "admin"} and getattr(self, "action", None) == "list":
            return queryset.filter(status=EmployeeLeave.Status.REQUESTED)
        return queryset

    def perform_create(self, serializer):
        if getattr(self.request.user, "role", "") != "employee":
            serializer.save()
            return

        employee_profile = getattr(self.request.user, "employee_profile", None)
        if employee_profile is None:
            raise PermissionDenied("Employee profile is required.")
        if serializer.validated_data["employee"].id != employee_profile.id:
            raise PermissionDenied("You can only manage your own leaves.")
        serializer.save(status=EmployeeLeave.Status.REQUESTED)

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        leave = self.get_object()
        serializer = EmployeeLeaveStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if leave.status != EmployeeLeave.Status.REQUESTED:
            return Response(
                {"detail": "Only requested leaves can change status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        leave.status = serializer.validated_data["status"]
        leave.save(update_fields=["status", "updated_at"])
        response = EmployeeLeaveSerializer(leave)
        return Response(response.data, status=status.HTTP_200_OK)


class EmployeeAvailabilityOverrideViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAvailabilityOverride.objects.all().order_by("id")
    serializer_class = EmployeeAvailabilityOverrideSerializer
    permission_classes = [AvailabilityOverridePermission]


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by("id")
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]


class TaskRequirementViewSet(viewsets.ModelViewSet):
    queryset = TaskRequirement.objects.all().order_by("id")
    serializer_class = TaskRequirementSerializer
    permission_classes = [TaskRequirementPermission]


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all().order_by("id")
    serializer_class = AssignmentSerializer
    permission_classes = [AssignmentPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self.request.user, "role", "") == "employee":
            employee_profile = getattr(self.request.user, "employee_profile", None)
            if employee_profile is None:
                return Assignment.objects.none()
            return queryset.filter(employee_id=employee_profile.id)
        return queryset

    @action(detail=False, methods=["post"], url_path="manual")
    def manual(self, request):
        serializer = AssignmentManualCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(created_by_user=request.user)
        response = AssignmentSerializer(assignment)
        return Response(response.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="approve-proposal", permission_classes=[PlannerApprovalPermission])
    def approve_proposal(self, request):
        serializer = AssignmentApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assignment = serializer.save(approved_by_user=request.user)
        except PlannerServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        response = AssignmentSerializer(assignment)
        return Response(response.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        assignment = reject_assignment(assignment=self.get_object(), rejected_by_user=request.user)
        response = AssignmentSerializer(assignment)
        return Response(response.data, status=status.HTTP_200_OK)


class AssignmentChangeLogViewSet(viewsets.ModelViewSet):
    queryset = AssignmentChangeLog.objects.all().order_by("id")
    serializer_class = AssignmentChangeLogSerializer
    permission_classes = [AssignmentChangeLogPermission]
