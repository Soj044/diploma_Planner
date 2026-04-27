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
