"""DRF viewsets for MVP CRUD surface."""

from rest_framework import status, viewsets
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
