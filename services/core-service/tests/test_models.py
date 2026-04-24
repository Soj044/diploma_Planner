"""Core-service model and serializer checks for the MVP schema."""

from datetime import date
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings
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
from contracts.schemas import PlanningSnapshot


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

    def test_planning_snapshot_endpoint_exports_core_truth(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="snapshot-manager",
            email="snapshot-manager@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
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
        )

        self.assertEqual(response.status_code, 200)
        snapshot = PlanningSnapshot.model_validate(response.data)
        self.assertEqual(snapshot.tasks[0].task_id, str(task.id))
        self.assertEqual(snapshot.tasks[0].starts_at.isoformat(), "2026-05-02T00:00:00+00:00")
        self.assertEqual(snapshot.tasks[0].ends_at.isoformat(), "2026-05-03T00:00:00+00:00")
        self.assertEqual(snapshot.employees[0].employee_id, str(employee.id))
        override_slot = next(slot for slot in snapshot.employees[0].availability if slot.start_at.date() == date(2026, 5, 2))
        self.assertEqual(override_slot.available_hours, 4)

    def test_planning_snapshot_endpoint_requires_authentication(self) -> None:
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

    def test_planning_snapshot_endpoint_skips_tasks_starting_before_period(self) -> None:
        user_model = get_user_model()
        manager = user_model.objects.create_user(
            username="snapshot-period-manager",
            email="snapshot-period-manager@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=manager)
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
        )

        self.assertEqual(response.status_code, 200)
        snapshot = PlanningSnapshot.model_validate(response.data)
        self.assertEqual(snapshot.tasks, [])
