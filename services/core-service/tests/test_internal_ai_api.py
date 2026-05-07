"""API tests for internal core-service AI helper endpoints."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from operations.models import (
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


@override_settings(INTERNAL_SERVICE_TOKEN="ai-layer-shared-token")
class InternalAiApiTests(APITestCase):
    """Verify that internal AI helper endpoints stay token-protected."""

    def setUp(self) -> None:
        """Create a compact assignment dataset reused by the internal AI tests."""

        user_model = get_user_model()
        self.manager_user = user_model.objects.create_user(
            username="manager-ai-test",
            email="manager-ai@example.com",
            password="pass12345",
            role="manager",
        )
        self.department = Department.objects.create(name="Assembly")
        self.python_skill = Skill.objects.create(name="Python")
        self.safety_skill = Skill.objects.create(name="Safety")
        self.employee_user = user_model.objects.create_user(
            username="employee-ai-test",
            email="employee-ai@example.com",
            password="pass12345",
            role="employee",
        )
        self.employee = Employee.objects.create(
            user=self.employee_user,
            department=self.department,
            full_name="Alice Worker",
            position_name="Assembler",
            employment_type=Employee.EmploymentType.FULL_TIME,
            weekly_capacity_hours=40,
            timezone="UTC",
            is_active=True,
        )
        self.employee_skill = EmployeeSkill.objects.create(
            employee=self.employee,
            skill=self.python_skill,
            level=4,
        )
        self.task = Task.objects.create(
            department=self.department,
            title="Assemble batch",
            description="Prepare the batch for delivery",
            status=Task.Status.PLANNED,
            priority=Task.Priority.HIGH,
            estimated_hours=6,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=1),
            created_by_user=self.manager_user,
        )
        self.task_requirement = TaskRequirement.objects.create(
            task=self.task,
            skill=self.python_skill,
            min_level=3,
            weight="1.50",
        )
        self.assignment = Assignment.objects.create(
            task=self.task,
            employee=self.employee,
            source_plan_run_id=None,
            planned_hours=6,
            start_date=self.task.start_date,
            end_date=self.task.due_date,
            status=Assignment.Status.APPROVED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=self.manager_user,
            approved_by_user=self.manager_user,
            approved_at=timezone.now(),
            notes="Approved from manager review",
        )
        self.schedule = WorkSchedule.objects.create(
            employee=self.employee,
            name="Default",
            is_default=True,
        )
        WorkScheduleDay.objects.create(
            schedule=self.schedule,
            weekday=self.task.start_date.weekday(),
            is_working_day=True,
            capacity_hours=8,
        )
        WorkScheduleDay.objects.create(
            schedule=self.schedule,
            weekday=(self.task.start_date.weekday() + 1) % 7,
            is_working_day=False,
            capacity_hours=0,
        )
        EmployeeLeave.objects.create(
            employee=self.employee,
            leave_type=EmployeeLeave.LeaveType.DAY_OFF,
            status=EmployeeLeave.Status.APPROVED,
            start_date=self.task.start_date,
            end_date=self.task.start_date,
            comment="Doctor visit",
        )
        EmployeeLeave.objects.create(
            employee=self.employee,
            leave_type=EmployeeLeave.LeaveType.VACATION,
            status=EmployeeLeave.Status.APPROVED,
            start_date=self.task.due_date + timedelta(days=5),
            end_date=self.task.due_date + timedelta(days=6),
            comment="Future leave",
        )
        EmployeeAvailabilityOverride.objects.create(
            employee=self.employee,
            date=self.task.due_date,
            available_hours=4,
            reason="Half shift",
            created_by_user=self.manager_user,
        )
        EmployeeAvailabilityOverride.objects.create(
            employee=self.employee,
            date=self.task.due_date + timedelta(days=7),
            available_hours=2,
            reason="Later override",
            created_by_user=self.manager_user,
        )
        AssignmentChangeLog.objects.create(
            assignment=self.assignment,
            old_employee=None,
            new_employee=self.employee,
            change_reason="Created assignment",
            changed_by_user=self.manager_user,
        )

    def test_internal_ai_boundary_requires_internal_token(self) -> None:
        """Reject anonymous access to the internal AI service-boundary endpoint."""

        response = self.client.get("/api/v1/internal/ai/service-boundary/")

        assert response.status_code in {401, 403}

    def test_internal_ai_boundary_accepts_valid_internal_token(self) -> None:
        """Allow trusted internal callers and return the core-service boundary payload."""

        response = self.client.get(
            "/api/v1/internal/ai/service-boundary/",
            HTTP_X_INTERNAL_SERVICE_TOKEN="ai-layer-shared-token",
        )

        assert response.status_code == 200
        assert response.json()["service"] == "core-service"
        assert response.json()["responsibility"] == "business truth"

    def test_internal_ai_index_feed_requires_internal_token(self) -> None:
        """Reject anonymous access to the internal AI index-feed endpoint."""

        response = self.client.get("/api/v1/internal/ai/index-feed/")

        assert response.status_code in {401, 403}

    def test_internal_ai_index_feed_returns_assignment_case_upsert(self) -> None:
        """Return a flattened assignment_case upsert item for successful assignments."""

        response = self.client.get(
            "/api/v1/internal/ai/index-feed/",
            HTTP_X_INTERNAL_SERVICE_TOKEN="ai-layer-shared-token",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_service"] == "core-service"
        assert len(payload["items"]) == 1
        item = payload["items"][0]
        assert item["source_type"] == "assignment_case"
        assert item["source_key"] == f"assignment:{self.assignment.id}"
        assert item["index_action"] == "upsert"
        assert item["metadata"]["task_id"] == str(self.task.id)
        assert item["metadata"]["employee_id"] == str(self.employee.id)

    def test_internal_ai_index_feed_returns_delete_after_reject(self) -> None:
        """Return a delete action when a previously indexed assignment becomes rejected."""

        self.assignment.status = Assignment.Status.REJECTED
        self.assignment.save(update_fields=["status"])
        AssignmentChangeLog.objects.create(
            assignment=self.assignment,
            old_employee=self.employee,
            new_employee=None,
            change_reason="Rejected assignment",
            changed_by_user=self.manager_user,
        )

        changed_since = (timezone.now() - timedelta(minutes=5)).isoformat()
        response = self.client.get(
            "/api/v1/internal/ai/index-feed/",
            {"changed_since": changed_since},
            HTTP_X_INTERNAL_SERVICE_TOKEN="ai-layer-shared-token",
        )

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["source_key"] == f"assignment:{self.assignment.id}"
        assert item["index_action"] == "delete"

    def test_internal_ai_index_feed_filters_by_changed_since(self) -> None:
        """Skip assignments whose flattened source timestamp is not newer than the cursor."""

        changed_since = (timezone.now() + timedelta(minutes=5)).isoformat()
        response = self.client.get(
            "/api/v1/internal/ai/index-feed/",
            {"changed_since": changed_since},
            HTTP_X_INTERNAL_SERVICE_TOKEN="ai-layer-shared-token",
        )

        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_internal_ai_assignment_context_returns_relevant_live_slice(self) -> None:
        """Return task requirements, employee skills, and only the availability slice for the task window."""

        response = self.client.get(
            f"/api/v1/internal/ai/tasks/{self.task.id}/assignment-context/?employee_id={self.employee.id}",
            HTTP_X_INTERNAL_SERVICE_TOKEN="ai-layer-shared-token",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["task"]["id"] == str(self.task.id)
        assert payload["employee"]["id"] == str(self.employee.id)
        assert payload["requirements"][0]["skill_name"] == "Python"
        assert payload["employee_skills"][0]["skill_name"] == "Python"
        assert len(payload["availability"]["approved_leaves"]) == 1
        assert len(payload["availability"]["availability_overrides"]) == 1
        assert len(payload["availability"]["schedule_days"]) == 2

    def test_internal_ai_assignment_context_requires_internal_token(self) -> None:
        """Reject anonymous access to the live assignment-context endpoint."""

        response = self.client.get(
            f"/api/v1/internal/ai/tasks/{self.task.id}/assignment-context/?employee_id={self.employee.id}",
        )

        assert response.status_code in {401, 403}
