"""HTTP clients for ai-layer calls into core-service.

This module keeps auth authority in core-service and centralizes the shared
internal-token client that ai-layer will use for browser token introspection and
future internal AI helper reads such as retrieval feeds and live assignment
context payloads.
"""

from datetime import datetime
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.dtos import AssignmentLiveContext, IndexFeedEnvelope


class CoreServiceClientError(Exception):
    """Raised when a core-service client call fails or returns an unusable payload."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class CoreServiceAuthError(CoreServiceClientError):
    """Raised when token introspection fails or core-service auth is unavailable."""


class CoreServiceBoundaryError(CoreServiceClientError):
    """Raised when internal AI boundary reads from core-service fail."""


class CoreServiceAiReadError(CoreServiceClientError):
    """Raised when internal AI feeds or live context reads from core-service fail."""


@dataclass(frozen=True)
class AuthenticatedUserContext:
    """Compact user context returned by core-service token introspection."""

    user_id: int
    role: str
    is_active: bool
    employee_id: int | None


@dataclass(frozen=True)
class CoreServiceBoundaryPayload:
    """Compact payload describing the core-service ownership boundary."""

    service: str
    responsibility: str
    owns: list[str]


class CoreServiceAuthClient:
    """Call core-service for ai-layer auth and internal helper reads."""

    def __init__(
        self,
        base_url: str,
        internal_service_token: str = "",
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Configure the core-service client with base URL and shared token."""

        self._base_url = base_url.rstrip("/")
        self._internal_service_token = internal_service_token
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def introspect_access_token(self, access_token: str) -> AuthenticatedUserContext:
        """Resolve a Bearer token into a compact authenticated user context."""

        if not self._internal_service_token:
            raise CoreServiceAuthError(status_code=503, detail="ai-layer auth introspection is not configured")

        payload = self._request_json(
            method="POST",
            path="/api/v1/auth/introspect",
            json_body={"token": access_token},
            error_cls=CoreServiceAuthError,
            unavailable_detail="core-service auth introspection is unavailable",
            passthrough_status_codes={401, 403},
        )

        try:
            user_id = int(payload["user_id"])
            role = str(payload["role"])
            is_active = bool(payload["is_active"])
            employee_raw = payload.get("employee_id")
            employee_id = int(employee_raw) if employee_raw is not None else None
        except (KeyError, TypeError, ValueError) as exc:
            raise CoreServiceAuthError(
                status_code=503,
                detail="core-service returned invalid introspection payload",
            ) from exc

        return AuthenticatedUserContext(
            user_id=user_id,
            role=role,
            is_active=is_active,
            employee_id=employee_id,
        )

    def get_internal_ai_service_boundary(self) -> CoreServiceBoundaryPayload:
        """Read the internal AI ownership boundary payload from core-service."""

        if not self._internal_service_token:
            raise CoreServiceBoundaryError(status_code=503, detail="ai-layer internal core-service access is not configured")

        payload = self._request_json(
            method="GET",
            path="/api/v1/internal/ai/service-boundary/",
            error_cls=CoreServiceBoundaryError,
            unavailable_detail="core-service internal AI boundary is unavailable",
            passthrough_status_codes={401, 403, 503},
        )
        return self._parse_boundary_payload(payload)

    def list_index_feed(self, changed_since: datetime | None) -> IndexFeedEnvelope:
        """Read the flattened `assignment_case` feed used by ai-layer sync."""

        if not self._internal_service_token:
            raise CoreServiceAiReadError(status_code=503, detail="ai-layer internal core-service access is not configured")

        payload = self._request_json(
            method="GET",
            path="/api/v1/internal/ai/index-feed/",
            query_params={"changed_since": changed_since.isoformat()} if changed_since else None,
            error_cls=CoreServiceAiReadError,
            unavailable_detail="core-service internal AI index feed is unavailable",
            passthrough_status_codes={401, 403, 404},
        )
        return self._parse_index_feed_payload(payload)

    def get_assignment_context(self, *, task_id: str, employee_id: str) -> AssignmentLiveContext:
        """Read one live task-plus-employee assignment explanation context."""

        if not self._internal_service_token:
            raise CoreServiceAiReadError(status_code=503, detail="ai-layer internal core-service access is not configured")

        payload = self._request_json(
            method="GET",
            path=f"/api/v1/internal/ai/tasks/{task_id}/assignment-context/",
            query_params={"employee_id": employee_id},
            error_cls=CoreServiceAiReadError,
            unavailable_detail="core-service internal AI assignment context is unavailable",
            passthrough_status_codes={401, 403, 404},
        )
        return self._parse_assignment_context_payload(payload)

    def _build_headers(self) -> dict[str, str]:
        """Build headers for internal ai-layer calls to core-service."""

        return {
            "Content-Type": "application/json",
            "X-Internal-Service-Token": self._internal_service_token,
        }

    def _parse_boundary_payload(self, payload: dict[str, object]) -> CoreServiceBoundaryPayload:
        """Validate and map one internal boundary payload from core-service."""

        try:
            service = str(payload["service"])
            responsibility = str(payload["responsibility"])
            owns = [str(item) for item in payload["owns"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise CoreServiceBoundaryError(
                status_code=503,
                detail="core-service returned invalid internal AI boundary payload",
            ) from exc
        return CoreServiceBoundaryPayload(
            service=service,
            responsibility=responsibility,
            owns=owns,
        )

    def _parse_index_feed_payload(self, payload: dict[str, object]) -> IndexFeedEnvelope:
        """Validate one internal AI index-feed payload returned by core-service."""

        try:
            return IndexFeedEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise CoreServiceAiReadError(
                status_code=502,
                detail="core-service returned invalid internal AI index feed payload",
            ) from exc

    def _parse_assignment_context_payload(self, payload: dict[str, object]) -> AssignmentLiveContext:
        """Validate one live assignment explanation context from core-service."""

        try:
            return AssignmentLiveContext.model_validate(payload)
        except ValidationError as exc:
            raise CoreServiceAiReadError(
                status_code=502,
                detail="core-service returned invalid internal AI assignment context payload",
            ) from exc

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        error_cls: type[CoreServiceClientError],
        unavailable_detail: str,
        passthrough_status_codes: set[int],
        json_body: dict[str, object] | None = None,
        query_params: dict[str, str] | None = None,
    ) -> dict[str, object]:
        """Execute one JSON request against core-service and map errors consistently."""

        try:
            with httpx.Client(
                base_url=self._base_url,
                headers=self._build_headers(),
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.request(
                    method=method,
                    url=path,
                    json=json_body,
                    params=query_params,
                )
        except httpx.HTTPError as exc:
            raise error_cls(status_code=503, detail=unavailable_detail) from exc

        if response.status_code >= 400:
            detail = self._extract_detail(response, fallback_detail=unavailable_detail)
            status_code = response.status_code if response.status_code in passthrough_status_codes else 503
            detail = detail if status_code in passthrough_status_codes else unavailable_detail
            raise error_cls(status_code=status_code, detail=detail)

        try:
            payload = response.json()
        except ValueError as exc:
            raise error_cls(status_code=503, detail=unavailable_detail) from exc
        if not isinstance(payload, dict):
            raise error_cls(status_code=503, detail=unavailable_detail)
        return payload

    def _extract_detail(self, response: httpx.Response, *, fallback_detail: str) -> str:
        """Extract a stable `detail` field from an error response when possible."""

        try:
            payload = response.json()
        except ValueError:
            return fallback_detail
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, str) and detail.strip():
            return detail
        return fallback_detail
