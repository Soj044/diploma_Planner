"""API tests for employee profile auto-creation on user create and role changes."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from operations.models import Employee


class UserEmployeeProfileSyncApiTests(APITestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="admin-sync",
            email="admin-sync@example.com",
            password="test-pass-123",
            role=user_model.Role.ADMIN,
        )
        self.client.force_authenticate(self.admin)

    def test_create_manager_user_creates_employee_profile(self) -> None:
        response = self.client.post(
            "/api/v1/users/",
            {
                "email": "manager-sync@example.com",
                "username": "manager-sync",
                "password": "test-pass-123",
                "first_name": "Manager",
                "last_name": "Sync",
                "role": "manager",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_model = get_user_model()
        user = user_model.objects.get(id=response.data["id"])
        profile = Employee.objects.get(user=user)
        self.assertEqual(profile.full_name, "Manager Sync")
        self.assertEqual(profile.position_name, "Pending assignment")
        self.assertEqual(profile.weekly_capacity_hours, 40)
        self.assertEqual(profile.timezone, "UTC")

    def test_create_admin_user_does_not_create_employee_profile(self) -> None:
        response = self.client.post(
            "/api/v1/users/",
            {
                "email": "admin-only@example.com",
                "username": "admin-only",
                "password": "test-pass-123",
                "role": "admin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_model = get_user_model()
        user = user_model.objects.get(id=response.data["id"])
        self.assertFalse(Employee.objects.filter(user=user).exists())

    def test_role_change_from_admin_to_employee_creates_employee_profile(self) -> None:
        user_model = get_user_model()
        target = user_model.objects.create_user(
            username="target-admin",
            email="target-admin@example.com",
            password="test-pass-123",
            role=user_model.Role.ADMIN,
            first_name="Role",
            last_name="Changed",
        )
        self.assertFalse(Employee.objects.filter(user=target).exists())

        response = self.client.patch(
            f"/api/v1/users/{target.id}/",
            {"role": "employee"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile = Employee.objects.get(user=target)
        self.assertEqual(profile.full_name, "Role Changed")

    def test_role_change_from_employee_to_admin_keeps_employee_profile(self) -> None:
        user_model = get_user_model()
        target = user_model.objects.create_user(
            username="target-employee",
            email="target-employee@example.com",
            password="test-pass-123",
            role=user_model.Role.EMPLOYEE,
        )
        profile = Employee.objects.create(
            user=target,
            full_name="Target Employee",
            position_name="Operator",
        )

        response = self.client.patch(
            f"/api/v1/users/{target.id}/",
            {"role": "admin"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Employee.objects.filter(id=profile.id, user=target).exists())
