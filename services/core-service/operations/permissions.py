"""Custom permissions for internal planner integration."""

import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasPlannerServiceAccess(BasePermission):
    """Allow authenticated users or planner-service with a shared internal token."""

    message = "Authentication credentials were not provided."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return True

        internal_token = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")
        request_token = request.headers.get("X-Internal-Service-Token", "")
        if not internal_token or not request_token:
            return False

        return secrets.compare_digest(request_token, internal_token)
