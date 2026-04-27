"""Permission helpers for auth and service-to-service user token checks."""

import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasInternalServiceToken(BasePermission):
    """Allow access only when a valid internal service token header is provided."""

    message = "Internal service credentials were not provided."

    def has_permission(self, request, view) -> bool:
        expected_token = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")
        provided_token = request.headers.get("X-Internal-Service-Token", "")
        if not expected_token or not provided_token:
            return False
        return secrets.compare_digest(provided_token, expected_token)


class IsAdminRole(BasePermission):
    """Allow access only for authenticated active users with admin role."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_active and getattr(user, "role", "") == "admin")
