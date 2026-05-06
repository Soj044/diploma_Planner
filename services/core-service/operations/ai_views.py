"""Internal AI helper endpoints for core-service.

This file exposes read-only internal endpoints that describe the core-service
truth boundary for ai-layer integration. Access is restricted to requests that
carry the shared internal service token header.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import HasInternalServiceToken


class InternalAiServiceBoundaryView(APIView):
    """Expose the core-service ownership boundary for trusted internal AI calls."""

    permission_classes = [HasInternalServiceToken]

    def get(self, request):
        """Return a compact description of the business-truth boundary."""

        return Response(
            {
                "service": "core-service",
                "responsibility": "business truth",
                "owns": [
                    "users",
                    "employees",
                    "departments",
                    "skills",
                    "schedules",
                    "leaves",
                    "tasks",
                    "final assignments",
                ],
            }
        )
