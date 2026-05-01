"""Core-service model and serializer checks for the MVP schema."""

from datetime import date
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from contracts.schemas import AssignmentProposal, PlanResponse, PlanRunArtifacts, PlanRunSummary, PlanningSnapshot
from operations.models import (
    Assignment,
    Department,
    Employee,
    EmployeeAvailabilityOverride,
    EmployeeLeave,
    EmployeeSkill,
    Skill,
    Task,
    WorkSchedule,
    WorkScheduleDay,
)
from operations.planner_client import PlannerServiceError
from operations.serializers import AssignmentSerializer, EmployeeLeaveSerializer, TaskSerializer, WorkScheduleDaySerializer


class CoreModelTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        self.department = Department.objects.create(name="Operations")
        self.skill = Skill.objects.create(name="Python")
        self.employee = Employee.objects.create(
            user=self.user,
            department=self.department,
            full_name="Jane Manager",
            position_name="Planner",
        )

    def test_employee_skill_is_unique_per_employee_and_skill(self) -> None:
        EmployeeSkill.objects.create(employee=self.employee, skill=self.skill, level=3)

        with self.assertRaises(IntegrityError):
            EmployeeSkill.objects.create(employee=self.employee, skill=self.skill, level=4)

    def test_schedule_day_is_unique_per_schedule_and_weekday(self) -> None:
        schedule = WorkSchedule.objects.create(employee=self.employee, name="Default")
        WorkScheduleDay.objects.create(schedule=schedule, weekday=0, capacity_hours=8)

        with self.assertRaises(IntegrityError):
            WorkScheduleDay.objects.create(schedule=schedule, weekday=0, capacity_hours=6)

    def test_availability_override_is_unique_per_employee_and_date(self) -> None:
        EmployeeAvailabilityOverride.objects.create(
            employee=self.employee,
            date=date(2026, 4, 23),
            available_hours=4,
            created_by_user=self.user,
        )

        with self.assertRaises(IntegrityError):
            EmployeeAvailabilityOverride.objects.create(
                employee=self.employee,
                date=date(2026, 4, 23),
                available_hours=2,
            )

    def test_core_defaults_match_mvp_schema(self) -> None:
        leave = EmployeeLeave.objects.create(
            employee=self.employee,
            leave_type=EmployeeLeave.LeaveType.VACATION,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
        )
        task = Task.objects.create(
            department=self.department,
            title="Prepare weekly schedule",
            estimated_hours=6,
            due_date=date(2026, 5, 4),
            created_by_user=self.user,
        )

        self.assertEqual(self.employee.employment_type, Employee.EmploymentType.FULL_TIME)
        self.assertEqual(self.employee.weekly_capacity_hours, 40)
        self.assertEqual(leave.status, EmployeeLeave.Status.APPROVED)
        self.assertEqual(task.status, Task.Status.DRAFT)
        self.assertEqual(task.priority, Task.Priority.MEDIUM)


class CoreSerializerTests(TestCase):
    def test_date_range_validation_rejects_invalid_periods(self) -> None:
        self.assertFalse(
            EmployeeLeaveSerializer(
                data={
                    "employee": 1,
                    "leave_type": EmployeeLeave.LeaveType.VACATION,
                    "start_date": "2026-05-03",
                    "end_date": "2026-05-01",
                }
            ).is_valid()
        )
        self.assertFalse(
            TaskSerializer(
                data={
                    "title": "Invalid task",
                    "estimated_hours": 1,
                    "start_date": "2026-05-03",
                    "due_date": "2026-05-01",
                    "created_by_user": 1,
                }
            ).is_valid()
        )
        self.assertFalse(
            AssignmentSerializer(
                data={
                    "task": 1,
                    "employee": 1,
                    "planned_hours": 2,
                    "start_date": "2026-05-03",
                    "end_date": "2026-05-01",
                }
            ).is_valid()
        )

    def test_weekday_validation_rejects_invalid_weekday(self) -> None:
        serializer = WorkScheduleDaySerializer(data={"schedule": 1, "weekday": 7, "capacity_hours": 8})

        self.assertFalse(serializer.is_valid())
        self.assertIn("weekday", serializer.errors)


class CoreApiSmokeTests(APITestCase):
    def test_department_crud_endpoint_creates_department(self) -> None:
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="api-user",
            email="api-user@example.com",
            password="test-pass",
            role=user_model.Role.ADMIN,
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/v1/departments/",
            {"name": "Dispatch", "description": "Daily operations"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Dispatch")

    def test_department_list_includes_employee_summaries_without_email(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="department-manager",
            email="department-manager@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="department-employee",
            email="department-employee@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Directory")
        Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Directory Employee",
            position_name="Operator",
        )

        response = self.client.get("/api/v1/departments/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["employees"][0]["full_name"], "Directory Employee")
        self.assertEqual(response.data[0]["employees"][0]["position_name"], "Operator")
        self.assertNotIn("email", response.data[0]["employees"][0])

    def test_manual_assignment_endpoint_creates_approved_assignment(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manual-manager",
            email="manual-manager@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="manual-employee",
            email="manual-employee@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Manual assignment")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Manual Employee",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Manual task",
            estimated_hours=3,
            start_date=date(2026, 5, 10),
            due_date=date(2026, 5, 12),
            created_by_user=manager,
        )

        response = self.client.post(
            "/api/v1/assignments/manual/",
            {
                "task": task.id,
                "employee": employee.id,
                "planned_hours": 3,
                "notes": "Manual fallback",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Assignment.Status.APPROVED)
        self.assertEqual(response.data["start_date"], "2026-05-10")
        self.assertEqual(response.data["end_date"], "2026-05-12")
        self.assertEqual(response.data["assigned_by_type"], Assignment.SourceType.MANAGER)
        self.assertIsNone(response.data["source_plan_run_id"])
        self.assertEqual(response.data["approved_by_user"], manager.id)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.ASSIGNED)

    def test_manual_assignment_endpoint_rejects_task_without_dates(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manual-missing-dates-manager",
            email="manual-missing-dates-manager@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="manual-missing-dates-employee",
            email="manual-missing-dates-employee@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Missing dates")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="No Dates Employee",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Manual task missing dates",
            estimated_hours=2,
            due_date=date(2026, 5, 13),
            created_by_user=manager,
        )

        response = self.client.post(
            "/api/v1/assignments/manual/",
            {
                "task": task.id,
                "employee": employee.id,
                "planned_hours": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("start_date and due_date", str(response.data))

    def test_reject_assignment_endpoint_marks_assignment_rejected(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="reject-manager",
            email="reject-manager@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="reject-employee",
            email="reject-employee@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Reject flow")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Reject Employee",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Rejectable assignment",
            estimated_hours=2,
            start_date=date(2026, 5, 14),
            due_date=date(2026, 5, 14),
            created_by_user=manager,
        )
        assignment = Assignment.objects.create(
            task=task,
            employee=employee,
            planned_hours=2,
            start_date=date(2026, 5, 14),
            end_date=date(2026, 5, 14),
            status=Assignment.Status.APPROVED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=manager,
            approved_by_user=manager,
            approved_at=timezone.now(),
        )

        response = self.client.post(f"/api/v1/assignments/{assignment.id}/reject/", {}, format="json")

        assignment.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(assignment.status, Assignment.Status.REJECTED)
        self.assertEqual(task.status, Task.Status.PLANNED)

    def test_manual_assignment_endpoint_rejects_second_final_assignment_for_task(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manual-duplicate-manager",
            email="manual-duplicate-manager@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="manual-duplicate-employee",
            email="manual-duplicate-employee@example.com",
            password="test-pass",
        )
        other_employee_user = user_model.objects.create_user(
            username="manual-duplicate-existing",
            email="manual-duplicate-existing@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Duplicate manual")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Duplicate Candidate",
            position_name="Operator",
        )
        other_employee = Employee.objects.create(
            user=other_employee_user,
            department=department,
            full_name="Existing Final Candidate",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Manual duplicate task",
            estimated_hours=2,
            start_date=date(2026, 5, 15),
            due_date=date(2026, 5, 15),
            created_by_user=manager,
        )
        Assignment.objects.create(
            task=task,
            employee=other_employee,
            planned_hours=2,
            start_date=date(2026, 5, 15),
            end_date=date(2026, 5, 15),
            status=Assignment.Status.APPROVED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=manager,
            approved_by_user=manager,
            approved_at=timezone.now(),
        )

        response = self.client.post(
            "/api/v1/assignments/manual/",
            {
                "task": task.id,
                "employee": employee.id,
                "planned_hours": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Task already has a final assignment", str(response.data))

    def test_rejected_assignment_allows_new_manual_assignment(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manual-retry-manager",
            email="manual-retry-manager@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="manual-retry-employee",
            email="manual-retry-employee@example.com",
            password="test-pass",
        )
        other_employee_user = user_model.objects.create_user(
            username="manual-retry-other",
            email="manual-retry-other@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Retry manual")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Retry Candidate",
            position_name="Operator",
        )
        other_employee = Employee.objects.create(
            user=other_employee_user,
            department=department,
            full_name="Rejected Candidate",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Retry task",
            estimated_hours=2,
            start_date=date(2026, 5, 16),
            due_date=date(2026, 5, 16),
            created_by_user=manager,
        )
        Assignment.objects.create(
            task=task,
            employee=other_employee,
            planned_hours=2,
            start_date=date(2026, 5, 16),
            end_date=date(2026, 5, 16),
            status=Assignment.Status.REJECTED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=manager,
            approved_by_user=manager,
            approved_at=timezone.now(),
        )

        response = self.client.post(
            "/api/v1/assignments/manual/",
            {
                "task": task.id,
                "employee": employee.id,
                "planned_hours": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Assignment.Status.APPROVED)

    @patch("operations.approvals.PlannerServiceClient.fetch_plan_run")
    def test_rejected_assignment_allows_approve_proposal_again(self, fetch_plan_run_mock) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="approve-retry-manager",
            email="approve-retry-manager@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="approve-retry-employee",
            email="approve-retry-employee@example.com",
            password="test-pass",
        )
        other_employee_user = user_model.objects.create_user(
            username="approve-retry-other",
            email="approve-retry-other@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Retry planner approval")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Retry Planner Candidate",
            position_name="Operator",
        )
        other_employee = Employee.objects.create(
            user=other_employee_user,
            department=department,
            full_name="Rejected Planner Candidate",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Retry planner approval task",
            estimated_hours=2,
            due_date=date(2026, 5, 17),
            created_by_user=manager,
        )
        Assignment.objects.create(
            task=task,
            employee=other_employee,
            planned_hours=2,
            start_date=date(2026, 5, 17),
            end_date=date(2026, 5, 17),
            status=Assignment.Status.REJECTED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=manager,
            approved_by_user=manager,
            approved_at=timezone.now(),
        )
        source_plan_run_id = uuid4()
        fetch_plan_run_mock.return_value = PlanResponse(
            summary=PlanRunSummary(
                plan_run_id=str(source_plan_run_id),
                status="completed",
                created_at=timezone.now(),
                planning_period_start=timezone.now(),
                planning_period_end=timezone.now(),
                assigned_count=1,
                unassigned_count=0,
            ),
            proposals=[
                AssignmentProposal(
                    task_id=str(task.id),
                    employee_id=str(employee.id),
                    score=1.25,
                    planned_hours=2,
                    start_date=date(2026, 5, 17),
                    end_date=date(2026, 5, 17),
                )
            ],
            unassigned=[],
            artifacts=PlanRunArtifacts(),
        )

        response = self.client.post(
            "/api/v1/assignments/approve-proposal/",
            {
                "task": task.id,
                "employee": employee.id,
                "source_plan_run_id": str(source_plan_run_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Assignment.Status.APPROVED)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.ASSIGNED)

    @patch("operations.approvals.PlannerServiceClient.fetch_plan_run")
    def test_approve_proposal_endpoint_creates_approved_assignment(self, fetch_plan_run_mock) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manager-api",
            email="manager-api@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="employee-api",
            email="employee-api@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Planning")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Alex Employee",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Approved task",
            estimated_hours=3,
            due_date=date(2026, 5, 4),
            created_by_user=manager,
        )
        source_plan_run_id = uuid4()
        fetch_plan_run_mock.return_value = PlanResponse(
            summary=PlanRunSummary(
                plan_run_id=str(source_plan_run_id),
                status="completed",
                created_at=timezone.now(),
                planning_period_start=timezone.now(),
                planning_period_end=timezone.now(),
                assigned_count=1,
                unassigned_count=0,
            ),
            proposals=[
                AssignmentProposal(
                    task_id=str(task.id),
                    employee_id=str(employee.id),
                    score=1.5,
                    planned_hours=3,
                    start_date=date(2026, 5, 2),
                    end_date=date(2026, 5, 2),
                )
            ],
            unassigned=[],
            artifacts=PlanRunArtifacts(),
        )

        response = self.client.post(
            "/api/v1/assignments/approve-proposal/",
            {
                "task": task.id,
                "employee": employee.id,
                "source_plan_run_id": str(source_plan_run_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "approved")
        self.assertEqual(response.data["approved_by_user"], manager.id)
        self.assertEqual(response.data["end_date"], "2026-05-04")
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.ASSIGNED)

    @patch("operations.approvals.PlannerServiceClient.fetch_plan_run")
    def test_approve_proposal_endpoint_rejects_missing_planner_proposal(self, fetch_plan_run_mock) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manager-missing",
            email="manager-missing@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="employee-missing",
            email="employee-missing@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Planning")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Morgan Employee",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Missing planner proposal",
            estimated_hours=2,
            due_date=date(2026, 5, 5),
            created_by_user=manager,
        )
        source_plan_run_id = uuid4()
        fetch_plan_run_mock.return_value = PlanResponse(
            summary=PlanRunSummary(
                plan_run_id=str(source_plan_run_id),
                status="completed",
                created_at=timezone.now(),
                planning_period_start=timezone.now(),
                planning_period_end=timezone.now(),
                assigned_count=0,
                unassigned_count=0,
            ),
            proposals=[],
            unassigned=[],
            artifacts=PlanRunArtifacts(),
        )

        response = self.client.post(
            "/api/v1/assignments/approve-proposal/",
            {
                "task": task.id,
                "employee": employee.id,
                "source_plan_run_id": str(source_plan_run_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Planner proposal not found", str(response.data))

    @patch("operations.approvals.PlannerServiceClient.fetch_plan_run")
    def test_approve_proposal_endpoint_is_idempotent_for_same_plan_run_and_pair(self, fetch_plan_run_mock) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manager-idempotent",
            email="manager-idempotent@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="employee-idempotent",
            email="employee-idempotent@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Planning")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Taylor Employee",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Idempotent approval task",
            estimated_hours=2,
            due_date=date(2026, 5, 6),
            created_by_user=manager,
        )
        source_plan_run_id = uuid4()
        fetch_plan_run_mock.return_value = PlanResponse(
            summary=PlanRunSummary(
                plan_run_id=str(source_plan_run_id),
                status="completed",
                created_at=timezone.now(),
                planning_period_start=timezone.now(),
                planning_period_end=timezone.now(),
                assigned_count=1,
                unassigned_count=0,
            ),
            proposals=[
                AssignmentProposal(
                    task_id=str(task.id),
                    employee_id=str(employee.id),
                    score=1.0,
                    planned_hours=2,
                    start_date=date(2026, 5, 6),
                    end_date=date(2026, 5, 6),
                )
            ],
            unassigned=[],
            artifacts=PlanRunArtifacts(),
        )

        payload = {
            "task": task.id,
            "employee": employee.id,
            "source_plan_run_id": str(source_plan_run_id),
        }
        first_response = self.client.post("/api/v1/assignments/approve-proposal/", payload, format="json")
        second_response = self.client.post("/api/v1/assignments/approve-proposal/", payload, format="json")

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(first_response.data["id"], second_response.data["id"])

    @patch("operations.approvals.PlannerServiceClient.fetch_plan_run")
    def test_approve_proposal_endpoint_returns_502_when_planner_is_unavailable(self, fetch_plan_run_mock) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manager-upstream",
            email="manager-upstream@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="employee-upstream",
            email="employee-upstream@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Planning")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Jordan Employee",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Upstream planner task",
            estimated_hours=2,
            due_date=date(2026, 5, 7),
            created_by_user=manager,
        )
        fetch_plan_run_mock.side_effect = PlannerServiceError("planner-service is unavailable during approval handoff")

        response = self.client.post(
            "/api/v1/assignments/approve-proposal/",
            {
                "task": task.id,
                "employee": employee.id,
                "source_plan_run_id": str(uuid4()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["detail"], "planner-service is unavailable during approval handoff")

    @patch("operations.approvals.PlannerServiceClient.fetch_plan_run")
    def test_approve_proposal_endpoint_rejects_second_final_assignment_for_task(self, fetch_plan_run_mock) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manager-duplicate-final",
            email="manager-duplicate-final@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="employee-duplicate-final",
            email="employee-duplicate-final@example.com",
            password="test-pass",
        )
        other_employee_user = user_model.objects.create_user(
            username="employee-existing-final",
            email="employee-existing-final@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Planning")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Primary Candidate",
            position_name="Operator",
        )
        other_employee = Employee.objects.create(
            user=other_employee_user,
            department=department,
            full_name="Existing Final Assignee",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Already assigned task",
            estimated_hours=2,
            due_date=date(2026, 5, 8),
            created_by_user=manager,
        )
        Assignment.objects.create(
            task=task,
            employee=other_employee,
            planned_hours=2,
            start_date=date(2026, 5, 8),
            end_date=date(2026, 5, 8),
            status=Assignment.Status.APPROVED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=manager,
            approved_by_user=manager,
            approved_at=timezone.now(),
        )
        source_plan_run_id = uuid4()
        fetch_plan_run_mock.return_value = PlanResponse(
            summary=PlanRunSummary(
                plan_run_id=str(source_plan_run_id),
                status="completed",
                created_at=timezone.now(),
                planning_period_start=timezone.now(),
                planning_period_end=timezone.now(),
                assigned_count=1,
                unassigned_count=0,
            ),
            proposals=[
                AssignmentProposal(
                    task_id=str(task.id),
                    employee_id=str(employee.id),
                    score=1.0,
                    planned_hours=2,
                    start_date=date(2026, 5, 8),
                    end_date=date(2026, 5, 8),
                )
            ],
            unassigned=[],
            artifacts=PlanRunArtifacts(),
        )

        response = self.client.post(
            "/api/v1/assignments/approve-proposal/",
            {
                "task": task.id,
                "employee": employee.id,
                "source_plan_run_id": str(source_plan_run_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Task already has a final assignment", str(response.data))

    @patch("operations.approvals.PlannerServiceClient.fetch_plan_run")
    def test_approve_proposal_endpoint_rejects_non_selected_proposal(self, fetch_plan_run_mock) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manager-non-selected",
            email="manager-non-selected@example.com",
            password="test-pass",
            role=user_model.Role.MANAGER,
        )
        employee_user = user_model.objects.create_user(
            username="employee-non-selected",
            email="employee-non-selected@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
        department = Department.objects.create(name="Planning")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Candidate Not Selected",
            position_name="Operator",
        )
        task = Task.objects.create(
            department=department,
            title="Non selected planner proposal",
            estimated_hours=2,
            due_date=date(2026, 5, 9),
            created_by_user=manager,
        )
        source_plan_run_id = uuid4()
        fetch_plan_run_mock.return_value = PlanResponse(
            summary=PlanRunSummary(
                plan_run_id=str(source_plan_run_id),
                status="completed",
                created_at=timezone.now(),
                planning_period_start=timezone.now(),
                planning_period_end=timezone.now(),
                assigned_count=1,
                unassigned_count=0,
            ),
            proposals=[
                AssignmentProposal(
                    task_id=str(task.id),
                    employee_id=str(employee.id),
                    score=0.5,
                    is_selected=False,
                    planned_hours=2,
                    start_date=date(2026, 5, 9),
                    end_date=date(2026, 5, 9),
                )
            ],
            unassigned=[],
            artifacts=PlanRunArtifacts(),
        )

        response = self.client.post(
            "/api/v1/assignments/approve-proposal/",
            {
                "task": task.id,
                "employee": employee.id,
                "source_plan_run_id": str(source_plan_run_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be selected", str(response.data))

    @override_settings(INTERNAL_SERVICE_TOKEN="planner-service-secret")
    def test_planning_snapshot_endpoint_exports_core_truth(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="snapshot-manager",
            email="snapshot-manager@example.com",
            password="test-pass",
        )
        employee_user = user_model.objects.create_user(
            username="snapshot-employee",
            email="snapshot-employee@example.com",
            password="test-pass",
        )
        department = Department.objects.create(name="Dispatch")
        skill = Skill.objects.create(name="Forklift")
        employee = Employee.objects.create(
            user=employee_user,
            department=department,
            full_name="Taylor Worker",
            position_name="Operator",
        )
        EmployeeSkill.objects.create(employee=employee, skill=skill, level=4)
        schedule = WorkSchedule.objects.create(employee=employee, name="Default", is_default=True)
        WorkScheduleDay.objects.create(schedule=schedule, weekday=4, capacity_hours=8)
        EmployeeAvailabilityOverride.objects.create(
            employee=employee,
            date=date(2026, 5, 2),
            available_hours=4,
            created_by_user=manager,
        )
        task = Task.objects.create(
            department=department,
            title="Move pallets",
            status=Task.Status.PLANNED,
            estimated_hours=4,
            due_date=date(2026, 5, 2),
            created_by_user=manager,
        )
        task.requirements.create(skill=skill, min_level=2, weight=1.5)

        response = self.client.post(
            "/api/v1/planning-snapshot/",
            {
                "planning_period_start": "2026-05-01",
                "planning_period_end": "2026-05-02",
                "initiated_by_user_id": str(manager.id),
                "department_id": str(department.id),
                "task_ids": [str(task.id)],
            },
            format="json",
            HTTP_X_INTERNAL_SERVICE_TOKEN="planner-service-secret",
        )

        self.assertEqual(response.status_code, 200)
        snapshot = PlanningSnapshot.model_validate(response.data)
        self.assertEqual(snapshot.tasks[0].task_id, str(task.id))
        self.assertEqual(snapshot.tasks[0].starts_at.isoformat(), "2026-05-02T00:00:00+00:00")
        self.assertEqual(snapshot.tasks[0].ends_at.isoformat(), "2026-05-03T00:00:00+00:00")
        self.assertEqual(snapshot.employees[0].employee_id, str(employee.id))
        override_slot = next(slot for slot in snapshot.employees[0].availability if slot.start_at.date() == date(2026, 5, 2))
        self.assertEqual(override_slot.available_hours, 4)

    def test_planning_snapshot_endpoint_requires_internal_service_token(self) -> None:
        response = self.client.post(
            "/api/v1/planning-snapshot/",
            {
                "planning_period_start": "2026-05-01",
                "planning_period_end": "2026-05-02",
                "initiated_by_user_id": str(uuid4()),
            },
            format="json",
        )

        self.assertIn(response.status_code, {401, 403})

    @override_settings(INTERNAL_SERVICE_TOKEN="planner-service-secret")
    def test_planning_snapshot_endpoint_accepts_internal_service_token(self) -> None:
        response = self.client.post(
            "/api/v1/planning-snapshot/",
            {
                "planning_period_start": "2026-05-01",
                "planning_period_end": "2026-05-02",
                "initiated_by_user_id": str(uuid4()),
            },
            format="json",
            HTTP_X_INTERNAL_SERVICE_TOKEN="planner-service-secret",
        )

        self.assertEqual(response.status_code, 200)
        snapshot = PlanningSnapshot.model_validate(response.data)
        self.assertEqual(snapshot.tasks, [])
        self.assertEqual(snapshot.employees, [])

    @override_settings(INTERNAL_SERVICE_TOKEN="planner-service-secret")
    def test_planning_snapshot_endpoint_skips_tasks_starting_before_period(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="snapshot-period-manager",
            email="snapshot-period-manager@example.com",
            password="test-pass",
        )
        department = Department.objects.create(name="Planning")
        Task.objects.create(
            department=department,
            title="Carry-over task",
            status=Task.Status.PLANNED,
            estimated_hours=2,
            start_date=date(2026, 4, 30),
            due_date=date(2026, 5, 2),
            created_by_user=manager,
        )

        response = self.client.post(
            "/api/v1/planning-snapshot/",
            {
                "planning_period_start": "2026-05-01",
                "planning_period_end": "2026-05-02",
                "initiated_by_user_id": str(manager.id),
                "department_id": str(department.id),
            },
            format="json",
            HTTP_X_INTERNAL_SERVICE_TOKEN="planner-service-secret",
        )

        self.assertEqual(response.status_code, 200)
        snapshot = PlanningSnapshot.model_validate(response.data)
        self.assertEqual(snapshot.tasks, [])
