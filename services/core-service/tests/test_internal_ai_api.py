"""API tests for internal core-service AI helper endpoints."""

from django.test import override_settings
from rest_framework.test import APITestCase


@override_settings(INTERNAL_SERVICE_TOKEN="ai-layer-shared-token")
class InternalAiApiTests(APITestCase):
    """Verify that internal AI helper endpoints stay token-protected."""

    def test_internal_ai_boundary_requires_internal_token(self) -> None:
        """Reject anonymous access to the internal AI service-boundary endpoint."""

        response = self.client.get("/api/v1/internal/ai/service-boundary/")

        assert response.status_code in {401, 403}

    def test_internal_ai_boundary_accepts_valid_internal_token(self) -> None:
        """Allow trusted internal callers and return the core-service boundary payload."""

        response = self.client.get(
            "/api/v1/internal/ai/service-boundary/",
            HTTP_X_INTERNAL_SERVICE_TOKEN="ai-layer-shared-token",
        )

        assert response.status_code == 200
        assert response.json()["service"] == "core-service"
        assert response.json()["responsibility"] == "business truth"
