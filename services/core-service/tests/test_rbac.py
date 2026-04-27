"""Role-based access tests for core-service endpoints."""

from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from operations.models import Department, Employee, Task, WorkSchedule


class CoreRbacApiTests(APITestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="rbac-admin",
            email="rbac-admin@example.com",
            password="test-pass-123",
            role=user_model.Role.ADMIN,
        )
        self.manager = user_model.objects.create_user(
            username="rbac-manager",
            email="rbac-manager@example.com",
            password="test-pass-123",
            role=user_model.Role.MANAGER,
        )
        self.employee_user = user_model.objects.create_user(
            username="rbac-employee",
            email="rbac-employee@example.com",
            password="test-pass-123",
            role=user_model.Role.EMPLOYEE,
        )
        self.other_employee_user = user_model.objects.create_user(
            username="rbac-employee-other",
            email="rbac-employee-other@example.com",
            password="test-pass-123",
            role=user_model.Role.EMPLOYEE,
        )

        self.department = Department.objects.create(name="RBAC Department")
        self.employee = Employee.objects.create(
            user=self.employee_user,
            department=self.department,
            full_name="RBAC Employee",
            position_name="Operator",
        )
        self.other_employee = Employee.objects.create(
            user=self.other_employee_user,
            department=self.department,
            full_name="RBAC Employee Other",
            position_name="Operator",
        )
        self.schedule = WorkSchedule.objects.create(employee=self.other_employee, name="Other schedule", is_default=True)
        self.task = Task.objects.create(
            department=self.department,
            title="RBAC visible task",
            estimated_hours=2,
            due_date=date(2026, 5, 30),
            created_by_user=self.manager,
        )

    def test_manager_cannot_create_department_but_can_list_departments(self) -> None:
        self.client.force_authenticate(self.manager)

        create_response = self.client.post(
            "/api/v1/departments/",
            {"name": "Denied dept", "description": ""},
            format="json",
        )
        list_response = self.client.get("/api/v1/departments/")

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

    def test_employee_can_list_tasks_but_cannot_create_tasks(self) -> None:
        self.client.force_authenticate(self.employee_user)

        list_response = self.client.get("/api/v1/tasks/")
        create_response = self.client.post(
            "/api/v1/tasks/",
            {
                "department": self.department.id,
                "title": "Denied task",
                "estimated_hours": 1,
                "due_date": "2026-05-30",
                "created_by_user": self.employee_user.id,
            },
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_approve_assignment(self) -> None:
        self.client.force_authenticate(self.employee_user)

        response = self.client.post(
            "/api/v1/assignments/approve-proposal/",
            {
                "task": self.task.id,
                "employee": self.employee.id,
                "source_plan_run_id": "59617c37-700f-4ab4-8cf7-f22c8c57288c",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_create_own_work_schedule_only(self) -> None:
        self.client.force_authenticate(self.employee_user)

        own_response = self.client.post(
            "/api/v1/work-schedules/",
            {"employee": self.employee.id, "name": "Own schedule", "is_default": True},
            format="json",
        )
        foreign_response = self.client.post(
            "/api/v1/work-schedules/",
            {"employee": self.other_employee.id, "name": "Foreign schedule", "is_default": True},
            format="json",
        )

        self.assertEqual(own_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(foreign_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_create_own_leave_only(self) -> None:
        self.client.force_authenticate(self.employee_user)

        own_response = self.client.post(
            "/api/v1/employee-leaves/",
            {
                "employee": self.employee.id,
                "leave_type": "vacation",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
            },
            format="json",
        )
        foreign_response = self.client.post(
            "/api/v1/employee-leaves/",
            {
                "employee": self.other_employee.id,
                "leave_type": "vacation",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
            },
            format="json",
        )

        self.assertEqual(own_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(foreign_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_edit_any_work_schedule(self) -> None:
        self.client.force_authenticate(self.manager)

        response = self.client.patch(
            f"/api/v1/work-schedules/{self.schedule.id}/",
            {"name": "Manager updated"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.name, "Manager updated")

    def test_non_admin_cannot_access_users_endpoint(self) -> None:
        self.client.force_authenticate(self.manager)
        manager_response = self.client.get("/api/v1/users/")

        self.client.force_authenticate(self.employee_user)
        employee_response = self.client.get("/api/v1/users/")

        self.assertEqual(manager_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(employee_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_users_endpoint(self) -> None:
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/v1/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
