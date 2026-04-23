"""Core-service model and serializer checks for the MVP schema."""

from datetime import date
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APITestCase

from operations.models import (
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
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/v1/departments/",
            {"name": "Dispatch", "description": "Daily operations"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Dispatch")

    def test_approve_proposal_endpoint_creates_approved_assignment(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="manager-api",
            email="manager-api@example.com",
            password="test-pass",
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

        response = self.client.post(
            "/api/v1/assignments/approve-proposal/",
            {
                "task": task.id,
                "employee": employee.id,
                "source_plan_run_id": str(source_plan_run_id),
                "planned_hours": 3,
                "start_date": "2026-05-02",
                "end_date": "2026-05-02",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "approved")
        self.assertEqual(response.data["approved_by_user"], manager.id)
