"""API tests for token auth flow in core-service."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


class AuthFlowApiTests(APITestCase):
    def setUp(self) -> None:
        self.user_model = get_user_model()

    def _create_user(self, *, email: str, username: str, role: str = "employee", is_active: bool = True):
        return self.user_model.objects.create_user(
            username=username,
            email=email,
            password="test-pass-123",
            role=role,
            is_active=is_active,
        )

    def test_signup_creates_employee_role_user_and_returns_tokens(self) -> None:
        response = self.client.post(
            "/api/v1/auth/signup",
            {
                "email": "signup@example.com",
                "password": "test-pass-123",
                "first_name": "Sign",
                "last_name": "Up",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "signup@example.com")
        self.assertEqual(response.data["user"]["role"], "employee")
        self.assertIsNotNone(response.data["user"]["employee_id"])
        self.assertEqual(response.data["user"]["employee_profile"]["full_name"], "Sign Up")
        self.assertEqual(response.data["user"]["employee_profile"]["position_name"], "Pending assignment")
        self.assertIn("refresh_token", response.cookies)

    def test_login_returns_access_and_refresh_cookie(self) -> None:
        self._create_user(email="manager-auth@example.com", username="manager-auth", role="manager")

        response = self.client.post(
            "/api/v1/auth/login",
            {"email": "manager-auth@example.com", "password": "test-pass-123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["role"], "manager")
        self.assertIn("refresh_token", response.cookies)

    def test_me_returns_authenticated_user_profile(self) -> None:
        self._create_user(email="me@example.com", username="me-user")
        login_response = self.client.post(
            "/api/v1/auth/login",
            {"email": "me@example.com", "password": "test-pass-123"},
            format="json",
        )
        access = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get("/api/v1/auth/me")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")
        self.assertEqual(response.data["role"], "employee")
        self.assertIn("employee_id", response.data)

    def test_refresh_issues_new_access_token_from_cookie(self) -> None:
        self._create_user(email="refresh@example.com", username="refresh-user")
        self.client.post(
            "/api/v1/auth/login",
            {"email": "refresh@example.com", "password": "test-pass-123"},
            format="json",
        )

        response = self.client.post("/api/v1/auth/refresh", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh_token", response.cookies)

    def test_logout_clears_refresh_cookie(self) -> None:
        self._create_user(email="logout@example.com", username="logout-user")
        self.client.post(
            "/api/v1/auth/login",
            {"email": "logout@example.com", "password": "test-pass-123"},
            format="json",
        )

        logout_response = self.client.post("/api/v1/auth/logout", {}, format="json")
        refresh_response = self.client.post("/api/v1/auth/refresh", {}, format="json")

        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_cannot_login(self) -> None:
        self._create_user(email="blocked@example.com", username="blocked-user", is_active=False)

        response = self.client.post(
            "/api/v1/auth/login",
            {"email": "blocked@example.com", "password": "test-pass-123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(INTERNAL_SERVICE_TOKEN="planner-test-token")
    def test_introspect_returns_user_context_for_valid_access_token(self) -> None:
        user = self._create_user(email="introspect@example.com", username="introspect-user", role="manager")
        login_response = self.client.post(
            "/api/v1/auth/login",
            {"email": "introspect@example.com", "password": "test-pass-123"},
            format="json",
        )

        response = self.client.post(
            "/api/v1/auth/introspect",
            {"token": login_response.data["access"]},
            format="json",
            HTTP_X_INTERNAL_SERVICE_TOKEN="planner-test-token",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], user.id)
        self.assertEqual(response.data["role"], "manager")
        self.assertTrue(response.data["is_active"])

    @override_settings(INTERNAL_SERVICE_TOKEN="planner-test-token")
    def test_introspect_rejects_inactive_user(self) -> None:
        user = self._create_user(email="inactive-intro@example.com", username="inactive-intro-user")
        login_response = self.client.post(
            "/api/v1/auth/login",
            {"email": "inactive-intro@example.com", "password": "test-pass-123"},
            format="json",
        )
        user.is_active = False
        user.save(update_fields=["is_active"])

        response = self.client.post(
            "/api/v1/auth/introspect",
            {"token": login_response.data["access"]},
            format="json",
            HTTP_X_INTERNAL_SERVICE_TOKEN="planner-test-token",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
