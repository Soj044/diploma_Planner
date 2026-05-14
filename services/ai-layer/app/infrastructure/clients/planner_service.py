"""HTTP client for ai-layer calls into planner-service.

This module keeps the planner-side internal helper boundary behind a dedicated
client so ai-layer can evolve toward real planner context reads, retrieval
feeds, and explanation contexts without routing those calls through the browser.
"""

from datetime import datetime
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.dtos import IndexFeedEnvelope, ProposalContext, UnassignedContext


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


class PlannerServiceAiReadError(PlannerServiceClientError):
    """Raised when planner-service AI feeds or persisted contexts fail."""


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
            detail = self._extract_detail(
                response,
                fallback_detail="planner-service internal AI boundary is unavailable",
            )
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

    def list_index_feed(self, changed_since: datetime | None) -> IndexFeedEnvelope:
        """Read the flattened `unassigned_case` feed used by ai-layer sync."""

        if not self._internal_service_token:
            raise PlannerServiceAiReadError(status_code=503, detail="ai-layer internal planner-service access is not configured")

        payload = self._request_json(
            path="/api/v1/internal/ai/index-feed",
            unavailable_detail="planner-service internal AI index feed is unavailable",
            passthrough_status_codes={401, 403, 404},
            query_params={"changed_since": changed_since.isoformat()} if changed_since else None,
        )
        try:
            return IndexFeedEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise PlannerServiceAiReadError(
                status_code=502,
                detail="planner-service returned invalid internal AI index feed payload",
            ) from exc

    def get_proposal_context(
        self,
        *,
        plan_run_id: str,
        task_id: str,
        employee_id: str,
    ) -> ProposalContext:
        """Read one persisted planner proposal context for ai-layer explanations."""

        payload = self._request_json(
            path=f"/api/v1/internal/ai/plan-runs/{plan_run_id}/proposal-context",
            unavailable_detail="planner-service internal AI proposal context is unavailable",
            passthrough_status_codes={401, 403, 404},
            query_params={"task_id": task_id, "employee_id": employee_id},
        )
        try:
            return ProposalContext.model_validate(payload)
        except ValidationError as exc:
            raise PlannerServiceAiReadError(
                status_code=502,
                detail="planner-service returned invalid internal AI proposal context payload",
            ) from exc

    def get_unassigned_context(
        self,
        *,
        plan_run_id: str,
        task_id: str,
    ) -> UnassignedContext:
        """Read one persisted unassigned-task context for ai-layer explanations."""

        payload = self._request_json(
            path=f"/api/v1/internal/ai/plan-runs/{plan_run_id}/unassigned-context",
            unavailable_detail="planner-service internal AI unassigned context is unavailable",
            passthrough_status_codes={401, 403, 404},
            query_params={"task_id": task_id},
        )
        try:
            return UnassignedContext.model_validate(payload)
        except ValidationError as exc:
            raise PlannerServiceAiReadError(
                status_code=502,
                detail="planner-service returned invalid internal AI unassigned context payload",
            ) from exc

    def _build_headers(self) -> dict[str, str]:
        """Build the shared internal headers for planner-service AI helper calls."""

        return {"X-Internal-Service-Token": self._internal_service_token}

    def _request_json(
        self,
        *,
        path: str,
        unavailable_detail: str,
        passthrough_status_codes: set[int],
        query_params: dict[str, str] | None = None,
    ) -> dict[str, object]:
        """Execute one JSON GET request against planner-service and map errors consistently."""

        if not self._internal_service_token:
            raise PlannerServiceClientError(status_code=503, detail="ai-layer internal planner-service access is not configured")

        try:
            with httpx.Client(
                base_url=self._base_url,
                headers=self._build_headers(),
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.get(path, params=query_params)
        except httpx.HTTPError as exc:
            raise PlannerServiceAiReadError(status_code=503, detail=unavailable_detail) from exc

        if response.status_code >= 400:
            detail = self._extract_detail(response, fallback_detail=unavailable_detail)
            status_code = response.status_code if response.status_code in passthrough_status_codes else 503
            detail = detail if status_code in passthrough_status_codes else unavailable_detail
            raise PlannerServiceAiReadError(status_code=status_code, detail=detail)

        try:
            payload = response.json()
        except ValueError as exc:
            raise PlannerServiceAiReadError(status_code=503, detail=unavailable_detail) from exc
        if not isinstance(payload, dict):
            raise PlannerServiceAiReadError(status_code=503, detail=unavailable_detail)
        return payload

    def _extract_detail(self, response: httpx.Response, *, fallback_detail: str) -> str:
        """Extract a stable error detail from planner-service helper responses."""

        try:
            payload = response.json()
        except ValueError:
            return fallback_detail
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, str) and detail.strip():
            return detail
        return fallback_detail
