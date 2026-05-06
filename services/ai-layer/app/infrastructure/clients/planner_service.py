"""HTTP client for ai-layer calls into planner-service.

This module keeps the planner-side internal helper boundary behind a dedicated
client so ai-layer can evolve toward real planner context reads without routing
those calls through the browser.
"""

from dataclasses import dataclass

import httpx


class PlannerServiceClientError(Exception):
    """Raised when planner-service internal AI helper calls fail or degrade."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class PlannerServiceBoundaryPayload:
    """Compact payload describing planner-service ownership for ai-layer callers."""

    service: str
    responsibility: str
    owns: list[str]


class PlannerServiceClient:
    """Call planner-service internal AI helper routes with the shared service token."""

    def __init__(
        self,
        base_url: str,
        internal_service_token: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Configure the planner-service client with base URL and shared auth token."""

        self._base_url = base_url.rstrip("/")
        self._internal_service_token = internal_service_token
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def get_internal_ai_service_boundary(self) -> PlannerServiceBoundaryPayload:
        """Read the planner-service ownership boundary for trusted internal callers."""

        if not self._internal_service_token:
            raise PlannerServiceClientError(status_code=503, detail="ai-layer internal planner-service access is not configured")

        try:
            with httpx.Client(
                base_url=self._base_url,
                headers=self._build_headers(),
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.get("/api/v1/internal/ai/service-boundary")
        except httpx.HTTPError as exc:
            raise PlannerServiceClientError(
                status_code=503,
                detail="planner-service internal AI boundary is unavailable",
            ) from exc

        if response.status_code >= 400:
            detail = self._extract_detail(response)
            status_code = response.status_code if response.status_code in {401, 403, 503} else 503
            detail = detail if status_code in {401, 403, 503} else "planner-service internal AI boundary is unavailable"
            raise PlannerServiceClientError(status_code=status_code, detail=detail)

        try:
            payload = response.json()
        except ValueError as exc:
            raise PlannerServiceClientError(
                status_code=503,
                detail="planner-service returned invalid internal AI boundary payload",
            ) from exc

        try:
            service = str(payload["service"])
            responsibility = str(payload["responsibility"])
            owns = [str(item) for item in payload["owns"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise PlannerServiceClientError(
                status_code=503,
                detail="planner-service returned invalid internal AI boundary payload",
            ) from exc

        return PlannerServiceBoundaryPayload(
            service=service,
            responsibility=responsibility,
            owns=owns,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build the shared internal headers for planner-service AI helper calls."""

        return {"X-Internal-Service-Token": self._internal_service_token}

    def _extract_detail(self, response: httpx.Response) -> str:
        """Extract a stable error detail from planner-service helper responses."""

        try:
            payload = response.json()
        except ValueError:
            return "planner-service internal AI boundary is unavailable"
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, str) and detail.strip():
            return detail
        return "planner-service internal AI boundary is unavailable"
