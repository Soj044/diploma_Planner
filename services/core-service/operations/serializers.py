"""DRF-сериализаторы core-service для задач, snapshot boundary и назначений.

Этот файл преобразует core модели в API payloads и обратно. Он используется
CRUD-viewsets, snapshot export и approval handoff, где менеджер утверждает
planner proposal и превращает его в финальный Assignment в core-service.
"""

from rest_framework import serializers

from .approvals import approve_planner_proposal, create_manual_assignment
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
from .task_workflow import create_task, update_task


class DepartmentEmployeeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ("id", "full_name", "position_name")
        read_only_fields = fields


class DepartmentSerializer(serializers.ModelSerializer):
    employees = DepartmentEmployeeSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Department
        fields = ("id", "name", "description", "employees", "created_at", "updated_at")
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

    def validate(self, attrs: dict) -> dict:
        is_working_day = attrs.get("is_working_day", getattr(self.instance, "is_working_day", True))
        capacity_hours = attrs.get("capacity_hours", getattr(self.instance, "capacity_hours", 0))
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))

        if not is_working_day:
            if capacity_hours != 0:
                raise serializers.ValidationError("Non-working days must have capacity_hours equal to 0.")
            if start_time is not None or end_time is not None:
                raise serializers.ValidationError("Non-working days must not define start_time or end_time.")
            return attrs

        if start_time and end_time:
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            if end_minutes <= start_minutes:
                raise serializers.ValidationError("end_time must be later than start_time.")
            window_hours = (end_minutes - start_minutes) / 60
            if capacity_hours > window_hours:
                raise serializers.ValidationError(
                    "capacity_hours cannot exceed the duration between start_time and end_time."
                )
        return attrs


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
        read_only_fields = ("id", "status", "created_at", "updated_at")

    def validate(self, attrs: dict) -> dict:
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Leave start_date must be before or equal to end_date.")
        return attrs


class EmployeeLeaveStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[EmployeeLeave.Status.APPROVED, EmployeeLeave.Status.REJECTED])


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


class SchedulePreviewQuerySerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    week_start = serializers.DateField()
    schedule_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)


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

    def create(self, validated_data: dict) -> Task:
        return create_task(validated_data=validated_data)

    def update(self, instance: Task, validated_data: dict) -> Task:
        return update_task(task=instance, validated_data=validated_data)


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
    source_plan_run_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        return attrs

    def create(self, validated_data: dict) -> Assignment:
        approved_by_user = validated_data.pop("approved_by_user")
        validated_data.setdefault("notes", "")
        return approve_planner_proposal(
            approved_by_user=approved_by_user,
            **validated_data,
        )


class AssignmentManualCreateSerializer(serializers.Serializer):
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all())
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    planned_hours = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data: dict) -> Assignment:
        created_by_user = validated_data.pop("created_by_user")
        validated_data.setdefault("notes", "")
        return create_manual_assignment(
            created_by_user=created_by_user,
            **validated_data,
        )


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
