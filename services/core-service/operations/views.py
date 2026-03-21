"""DRF viewsets for MVP CRUD surface."""

from rest_framework import viewsets

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
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class EmployeeSkillViewSet(viewsets.ModelViewSet):
    queryset = EmployeeSkill.objects.all()
    serializer_class = EmployeeSkillSerializer


class WorkScheduleViewSet(viewsets.ModelViewSet):
    queryset = WorkSchedule.objects.all()
    serializer_class = WorkScheduleSerializer


class WorkScheduleDayViewSet(viewsets.ModelViewSet):
    queryset = WorkScheduleDay.objects.all()
    serializer_class = WorkScheduleDaySerializer


class EmployeeLeaveViewSet(viewsets.ModelViewSet):
    queryset = EmployeeLeave.objects.all()
    serializer_class = EmployeeLeaveSerializer


class EmployeeAvailabilityOverrideViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAvailabilityOverride.objects.all()
    serializer_class = EmployeeAvailabilityOverrideSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


class TaskRequirementViewSet(viewsets.ModelViewSet):
    queryset = TaskRequirement.objects.all()
    serializer_class = TaskRequirementSerializer


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer


class AssignmentChangeLogViewSet(viewsets.ModelViewSet):
    queryset = AssignmentChangeLog.objects.all()
    serializer_class = AssignmentChangeLogSerializer
