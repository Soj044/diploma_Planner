"""Internal AI helper routes for planner-service.

This module exposes token-protected internal endpoints that document planner
ownership over proposals and diagnostics. They are intended for trusted
backend-to-backend calls from ai-layer and do not accept browser Bearer auth.
"""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import INTERNAL_SERVICE_TOKEN

router = APIRouter(prefix="/api/v1/internal/ai", tags=["internal-ai"])


def require_internal_ai_access(
    internal_service_token: str | None = Header(default=None, alias="X-Internal-Service-Token"),
) -> None:
    """Allow internal AI routes only when the shared service token matches exactly."""

    if not INTERNAL_SERVICE_TOKEN or not internal_service_token:
        raise HTTPException(status_code=401, detail="Internal service token is required.")
    if not secrets.compare_digest(internal_service_token, INTERNAL_SERVICE_TOKEN):
        raise HTTPException(status_code=403, detail="Internal service token is invalid.")


@router.get("/service-boundary", dependencies=[Depends(require_internal_ai_access)])
def get_internal_ai_service_boundary() -> dict[str, object]:
    """Return the planner-service truth boundary for trusted internal AI callers."""

    return {
        "service": "planner-service",
        "responsibility": "proposals and diagnostics truth",
        "owns": [
            "plan runs",
            "snapshots",
            "eligibility",
            "scores",
            "assignment proposals",
            "unassigned diagnostics",
            "solver statistics",
        ],
    }
