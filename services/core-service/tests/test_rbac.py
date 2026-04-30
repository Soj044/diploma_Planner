"""Role-based access tests for core-service endpoints."""

from datetime import date
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from operations.models import Assignment, Department, Employee, EmployeeLeave, Task, WorkSchedule, WorkScheduleDay


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
        self.own_schedule = WorkSchedule.objects.create(employee=self.employee, name="Own schedule", is_default=True)
        self.own_schedule_day = WorkScheduleDay.objects.create(
            schedule=self.own_schedule,
            weekday=0,
            capacity_hours=8,
        )
        self.schedule = WorkSchedule.objects.create(employee=self.other_employee, name="Other schedule", is_default=True)
        self.foreign_schedule_day = WorkScheduleDay.objects.create(
            schedule=self.schedule,
            weekday=1,
            capacity_hours=6,
        )
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

    def test_employee_can_only_read_own_work_schedule(self) -> None:
        self.client.force_authenticate(self.employee_user)

        list_response = self.client.get("/api/v1/work-schedules/")
        own_retrieve_response = self.client.get(f"/api/v1/work-schedules/{self.own_schedule.id}/")
        foreign_retrieve_response = self.client.get(f"/api/v1/work-schedules/{self.schedule.id}/")
        create_response = self.client.post(
            "/api/v1/work-schedules/",
            {"employee": self.employee.id, "name": "New own schedule", "is_default": True},
            format="json",
        )
        update_response = self.client.patch(
            f"/api/v1/work-schedules/{self.own_schedule.id}/",
            {"name": "Employee update denied"},
            format="json",
        )
        delete_response = self.client.delete(f"/api/v1/work-schedules/{self.own_schedule.id}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in list_response.data], [self.own_schedule.id])
        self.assertEqual(own_retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(foreign_retrieve_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_only_read_own_work_schedule_days(self) -> None:
        self.client.force_authenticate(self.employee_user)

        list_response = self.client.get("/api/v1/work-schedule-days/")
        own_retrieve_response = self.client.get(f"/api/v1/work-schedule-days/{self.own_schedule_day.id}/")
        foreign_retrieve_response = self.client.get(f"/api/v1/work-schedule-days/{self.foreign_schedule_day.id}/")
        create_response = self.client.post(
            "/api/v1/work-schedule-days/",
            {
                "schedule": self.own_schedule.id,
                "weekday": 2,
                "capacity_hours": 4,
            },
            format="json",
        )
        update_response = self.client.patch(
            f"/api/v1/work-schedule-days/{self.own_schedule_day.id}/",
            {"capacity_hours": 6},
            format="json",
        )
        delete_response = self.client.delete(f"/api/v1/work-schedule-days/{self.own_schedule_day.id}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in list_response.data], [self.own_schedule_day.id])
        self.assertEqual(own_retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(foreign_retrieve_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_leave_creation_is_requested_and_foreign_create_is_forbidden(self) -> None:
        self.client.force_authenticate(self.employee_user)

        own_response = self.client.post(
            "/api/v1/employee-leaves/",
            {
                "employee": self.employee.id,
                "leave_type": "vacation",
                "status": "approved",
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
        self.assertEqual(own_response.data["status"], EmployeeLeave.Status.REQUESTED)
        self.assertEqual(foreign_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_update_or_delete_only_requested_leave(self) -> None:
        requested_leave = EmployeeLeave.objects.create(
            employee=self.employee,
            leave_type=EmployeeLeave.LeaveType.VACATION,
            status=EmployeeLeave.Status.REQUESTED,
            start_date=date(2026, 6, 3),
            end_date=date(2026, 6, 3),
        )
        approved_leave = EmployeeLeave.objects.create(
            employee=self.employee,
            leave_type=EmployeeLeave.LeaveType.DAY_OFF,
            status=EmployeeLeave.Status.APPROVED,
            start_date=date(2026, 6, 4),
            end_date=date(2026, 6, 4),
        )
        self.client.force_authenticate(self.employee_user)

        update_requested_response = self.client.patch(
            f"/api/v1/employee-leaves/{requested_leave.id}/",
            {"comment": "Updated comment", "status": EmployeeLeave.Status.APPROVED},
            format="json",
        )
        update_approved_response = self.client.patch(
            f"/api/v1/employee-leaves/{approved_leave.id}/",
            {"comment": "Should fail"},
            format="json",
        )
        requested_leave.refresh_from_db()
        delete_approved_response = self.client.delete(f"/api/v1/employee-leaves/{approved_leave.id}/")
        delete_requested_response = self.client.delete(f"/api/v1/employee-leaves/{requested_leave.id}/")

        self.assertEqual(update_requested_response.status_code, status.HTTP_200_OK)
        self.assertEqual(requested_leave.comment, "Updated comment")
        self.assertEqual(requested_leave.status, EmployeeLeave.Status.REQUESTED)
        self.assertEqual(update_approved_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_approved_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_requested_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EmployeeLeave.objects.filter(id=requested_leave.id).exists())

    def test_manager_can_set_leave_status_but_cannot_edit_dates(self) -> None:
        requested_leave = EmployeeLeave.objects.create(
            employee=self.employee,
            leave_type=EmployeeLeave.LeaveType.VACATION,
            status=EmployeeLeave.Status.REQUESTED,
            start_date=date(2026, 6, 5),
            end_date=date(2026, 6, 5),
        )
        EmployeeLeave.objects.create(
            employee=self.employee,
            leave_type=EmployeeLeave.LeaveType.DAY_OFF,
            status=EmployeeLeave.Status.APPROVED,
            start_date=date(2026, 6, 6),
            end_date=date(2026, 6, 6),
        )
        self.client.force_authenticate(self.manager)

        list_response = self.client.get("/api/v1/employee-leaves/")
        set_status_response = self.client.post(
            f"/api/v1/employee-leaves/{requested_leave.id}/set-status/",
            {"status": EmployeeLeave.Status.APPROVED},
            format="json",
        )
        update_response = self.client.patch(
            f"/api/v1/employee-leaves/{requested_leave.id}/",
            {"end_date": "2026-06-07"},
            format="json",
        )

        requested_leave.refresh_from_db()
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in list_response.data], [requested_leave.id])
        self.assertEqual(set_status_response.status_code, status.HTTP_200_OK)
        self.assertEqual(requested_leave.status, EmployeeLeave.Status.APPROVED)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_set_leave_status(self) -> None:
        requested_leave = EmployeeLeave.objects.create(
            employee=self.employee,
            leave_type=EmployeeLeave.LeaveType.VACATION,
            status=EmployeeLeave.Status.REQUESTED,
            start_date=date(2026, 6, 8),
            end_date=date(2026, 6, 8),
        )
        self.client.force_authenticate(self.employee_user)

        response = self.client.post(
            f"/api/v1/employee-leaves/{requested_leave.id}/set-status/",
            {"status": EmployeeLeave.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_only_see_own_assignments(self) -> None:
        own_assignment = Assignment.objects.create(
            task=self.task,
            employee=self.employee,
            source_plan_run_id=uuid4(),
            planned_hours=2,
            start_date=date(2026, 5, 29),
            end_date=date(2026, 5, 30),
            status=Assignment.Status.APPROVED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=self.manager,
            approved_by_user=self.manager,
            approved_at=timezone.now(),
        )
        foreign_assignment = Assignment.objects.create(
            task=Task.objects.create(
                department=self.department,
                title="Foreign assignment task",
                estimated_hours=1,
                due_date=date(2026, 5, 31),
                created_by_user=self.manager,
            ),
            employee=self.other_employee,
            source_plan_run_id=uuid4(),
            planned_hours=1,
            start_date=date(2026, 5, 31),
            end_date=date(2026, 5, 31),
            status=Assignment.Status.APPROVED,
            assigned_by_type=Assignment.SourceType.MANAGER,
            assigned_by_user=self.manager,
            approved_by_user=self.manager,
            approved_at=timezone.now(),
        )
        self.client.force_authenticate(self.employee_user)

        list_response = self.client.get("/api/v1/assignments/")
        own_retrieve_response = self.client.get(f"/api/v1/assignments/{own_assignment.id}/")
        foreign_retrieve_response = self.client.get(f"/api/v1/assignments/{foreign_assignment.id}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in list_response.data], [own_assignment.id])
        self.assertEqual(own_retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(foreign_retrieve_response.status_code, status.HTTP_404_NOT_FOUND)

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
