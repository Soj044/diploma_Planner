"""DRF serializers for core-service business entities."""

from django.utils import timezone
from rest_framework import serializers

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


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name", "description", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "name", "description", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            "id",
            "user",
            "department",
            "full_name",
            "position_name",
            "employment_type",
            "weekly_capacity_hours",
            "timezone",
            "hire_date",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class EmployeeSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSkill
        fields = ("id", "employee", "skill", "level", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class WorkScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = ("id", "employee", "name", "is_default", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class WorkScheduleDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkScheduleDay
        fields = (
            "id",
            "schedule",
            "weekday",
            "is_working_day",
            "capacity_hours",
            "start_time",
            "end_time",
        )
        read_only_fields = ("id",)

    def validate_weekday(self, value: int) -> int:
        if value > 6:
            raise serializers.ValidationError("Weekday must be in range 0..6.")
        return value


class EmployeeLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeLeave
        fields = (
            "id",
            "employee",
            "leave_type",
            "status",
            "start_date",
            "end_date",
            "comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs: dict) -> dict:
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Leave start_date must be before or equal to end_date.")
        return attrs


class EmployeeAvailabilityOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeAvailabilityOverride
        fields = (
            "id",
            "employee",
            "date",
            "available_hours",
            "reason",
            "created_by_user",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "id",
            "department",
            "title",
            "description",
            "status",
            "priority",
            "estimated_hours",
            "actual_hours",
            "start_date",
            "due_date",
            "created_by_user",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs: dict) -> dict:
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        due_date = attrs.get("due_date", getattr(self.instance, "due_date", None))
        if start_date and due_date and start_date > due_date:
            raise serializers.ValidationError("Task start_date must be before or equal to due_date.")
        return attrs


class TaskRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskRequirement
        fields = ("id", "task", "skill", "min_level", "weight")
        read_only_fields = ("id",)


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = (
            "id",
            "task",
            "employee",
            "source_plan_run_id",
            "planned_hours",
            "start_date",
            "end_date",
            "status",
            "assigned_by_type",
            "assigned_by_user",
            "approved_by_user",
            "assigned_at",
            "approved_at",
            "notes",
        )
        read_only_fields = ("id", "assigned_at")

    def validate(self, attrs: dict) -> dict:
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Assignment start_date must be before or equal to end_date.")
        return attrs


class AssignmentApprovalSerializer(serializers.Serializer):
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all())
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    source_plan_run_id = serializers.UUIDField(required=False, allow_null=True)
    planned_hours = serializers.IntegerField(min_value=1)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError("Assignment start_date must be before or equal to end_date.")
        return attrs

    def create(self, validated_data: dict) -> Assignment:
        approved_by_user = validated_data.pop("approved_by_user")
        assignment = Assignment.objects.create(
            **validated_data,
            status=Assignment.Status.APPROVED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=approved_by_user,
            approved_by_user=approved_by_user,
            approved_at=timezone.now(),
        )
        AssignmentChangeLog.objects.create(
            assignment=assignment,
            old_employee=None,
            new_employee=assignment.employee,
            change_reason="Approved planner proposal",
            changed_by_user=approved_by_user,
        )
        return assignment


class AssignmentChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentChangeLog
        fields = (
            "id",
            "assignment",
            "old_employee",
            "new_employee",
            "change_reason",
            "changed_by_user",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
