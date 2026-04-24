"""DRF views for MVP CRUD surface and planner support."""

from contracts.schemas import CreatePlanRunRequest
from pydantic import ValidationError as PydanticValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

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
from .snapshots import build_planning_snapshot
from .serializers import (
    AssignmentChangeLogSerializer,
    AssignmentApprovalSerializer,
    AssignmentSerializer,
    DepartmentSerializer,
    EmployeeAvailabilityOverrideSerializer,
    EmployeeLeaveSerializer,
    EmployeeSerializer,
    EmployeeSkillSerializer,
    SkillSerializer,
    TaskRequirementSerializer,
    TaskSerializer,
    WorkScheduleDaySerializer,
    WorkScheduleSerializer,
)


class PlanningSnapshotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            payload = CreatePlanRunRequest.model_validate(request.data)
        except PydanticValidationError as exc:
            return Response({"detail": exc.errors()}, status=status.HTTP_400_BAD_REQUEST)

        snapshot = build_planning_snapshot(payload)
        return Response(snapshot.model_dump(mode="json"), status=status.HTTP_200_OK)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by("id")
    serializer_class = DepartmentSerializer


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all().order_by("id")
    serializer_class = SkillSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by("id")
    serializer_class = EmployeeSerializer


class EmployeeSkillViewSet(viewsets.ModelViewSet):
    queryset = EmployeeSkill.objects.all().order_by("id")
    serializer_class = EmployeeSkillSerializer


class WorkScheduleViewSet(viewsets.ModelViewSet):
    queryset = WorkSchedule.objects.all().order_by("id")
    serializer_class = WorkScheduleSerializer


class WorkScheduleDayViewSet(viewsets.ModelViewSet):
    queryset = WorkScheduleDay.objects.all().order_by("id")
    serializer_class = WorkScheduleDaySerializer


class EmployeeLeaveViewSet(viewsets.ModelViewSet):
    queryset = EmployeeLeave.objects.all().order_by("id")
    serializer_class = EmployeeLeaveSerializer


class EmployeeAvailabilityOverrideViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAvailabilityOverride.objects.all().order_by("id")
    serializer_class = EmployeeAvailabilityOverrideSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by("id")
    serializer_class = TaskSerializer


class TaskRequirementViewSet(viewsets.ModelViewSet):
    queryset = TaskRequirement.objects.all().order_by("id")
    serializer_class = TaskRequirementSerializer


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all().order_by("id")
    serializer_class = AssignmentSerializer

    @action(detail=False, methods=["post"], url_path="approve-proposal")
    def approve_proposal(self, request):
        serializer = AssignmentApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(approved_by_user=request.user)
        response = AssignmentSerializer(assignment)
        return Response(response.data, status=status.HTTP_201_CREATED)


class AssignmentChangeLogViewSet(viewsets.ModelViewSet):
    queryset = AssignmentChangeLog.objects.all().order_by("id")
    serializer_class = AssignmentChangeLogSerializer
