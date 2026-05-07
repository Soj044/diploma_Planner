"""Internal AI helper routes for planner-service.

This module exposes token-protected internal endpoints that document planner
ownership over proposals and diagnostics. They are intended for trusted
backend-to-backend calls from ai-layer and do not accept browser Bearer auth.
It also exposes flattened retrieval feeds and persisted context payloads built
from saved planner artifacts.
"""

from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import ValidationError
from starlette import status

from app.config import INTERNAL_SERVICE_TOKEN, PLANNER_DB_PATH
from app.infrastructure.repositories.sqlite import SqlitePlanRunRepository
from app.internal_ai_payloads import (
    build_proposal_context,
    build_unassigned_context,
    build_unassigned_index_feed,
)

router = APIRouter(prefix="/api/v1/internal/ai", tags=["internal-ai"])
repository = SqlitePlanRunRepository(db_path=PLANNER_DB_PATH)


def require_internal_ai_access(
    internal_service_token: str | None = Header(default=None, alias="X-Internal-Service-Token"),
) -> None:
    """Allow internal AI routes only when the shared service token matches exactly."""

    if not INTERNAL_SERVICE_TOKEN or not internal_service_token:
        raise HTTPException(status_code=401, detail="Internal service token is required.")
    if not secrets.compare_digest(internal_service_token, INTERNAL_SERVICE_TOKEN):
        raise HTTPException(status_code=403, detail="Internal service token is invalid.")


def _parse_changed_since(raw_changed_since: str | None) -> datetime | None:
    """Parse one optional UTC ISO8601 cursor used by ai-layer incremental sync."""

    if raw_changed_since is None or not raw_changed_since.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw_changed_since)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="changed_since must be a valid UTC ISO8601 datetime.",
        ) from exc
    if parsed.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="changed_since must include an explicit UTC offset.",
        )
    return parsed


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


@router.get("/index-feed", dependencies=[Depends(require_internal_ai_access)])
def get_internal_ai_index_feed(
    changed_since: str | None = Query(default=None),
) -> dict[str, object]:
    """Return the flattened `unassigned_case` feed for ai-layer incremental sync."""

    return build_unassigned_index_feed(repository, _parse_changed_since(changed_since))


@router.get(
    "/plan-runs/{plan_run_id}/proposal-context",
    dependencies=[Depends(require_internal_ai_access)],
)
def get_internal_ai_proposal_context(
    plan_run_id: str,
    task_id: str = Query(...),
    employee_id: str = Query(...),
) -> dict[str, object]:
    """Return one persisted proposal context payload for ai-layer explanations."""

    try:
        return build_proposal_context(
            repository,
            plan_run_id=plan_run_id,
            task_id=task_id,
            employee_id=employee_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Persisted plan run payload is invalid.",
        ) from exc


@router.get(
    "/plan-runs/{plan_run_id}/unassigned-context",
    dependencies=[Depends(require_internal_ai_access)],
)
def get_internal_ai_unassigned_context(
    plan_run_id: str,
    task_id: str = Query(...),
) -> dict[str, object]:
    """Return one persisted unassigned-task context payload for ai-layer explanations."""

    try:
        return build_unassigned_context(
            repository,
            plan_run_id=plan_run_id,
            task_id=task_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Persisted plan run payload is invalid.",
        ) from exc
