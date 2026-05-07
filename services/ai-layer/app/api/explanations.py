"""Public explanation routes for ai-layer.

This module defines the frontend-facing explanation contracts that managers and
admins will call. The responses remain advisory and can degrade with a
controlled `503` until the retrieval index is populated.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.application.explanations import (
    ExplanationIndexNotReadyError,
    ExplanationResult,
    ExplanationServiceError,
    ExplanationService,
)
from app.dependencies import get_explanation_service, require_ai_layer_access
from app.infrastructure.clients.core_service import AuthenticatedUserContext

router = APIRouter(prefix="/api/v1/explanations", tags=["explanations"])


class AssignmentRationaleRequest(BaseModel):
    """Request payload for explaining a proposed task-to-employee match."""

    task_id: str
    employee_id: str
    plan_run_id: str


class UnassignedTaskExplanationRequest(BaseModel):
    """Request payload for explaining why a task stayed unassigned."""

    task_id: str
    plan_run_id: str


class SimilarCasePayload(BaseModel):
    """Compact summary of one retrieved historical AI index match."""

    model_config = ConfigDict(from_attributes=True)

    headline: str
    source_service: str
    source_type: str
    source_key: str
    outcome_note: str


class AiExplanationPayload(BaseModel):
    """Shared HTTP response model for ai-layer explanations."""

    model_config = ConfigDict(from_attributes=True)

    summary: str
    reasons: list[str]
    risks: list[str]
    recommended_actions: list[str]
    similar_cases: list[SimilarCasePayload]
    advisory_note: str


def _build_response_payload(result: ExplanationResult) -> AiExplanationPayload:
    """Convert the internal explanation result into the public response schema."""

    return AiExplanationPayload.model_validate(result, from_attributes=True)


@router.post("/assignment-rationale", response_model=AiExplanationPayload)
def create_assignment_rationale(
    request: AssignmentRationaleRequest,
    context: AuthenticatedUserContext = Depends(require_ai_layer_access),
    service: ExplanationService = Depends(get_explanation_service),
) -> AiExplanationPayload:
    """Return an advisory explanation for one proposed assignment candidate."""

    try:
        result = service.build_assignment_rationale(
            task_id=request.task_id,
            employee_id=request.employee_id,
            plan_run_id=request.plan_run_id,
            user_context=context,
        )
    except ExplanationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _build_response_payload(result)


@router.post("/unassigned-task", response_model=AiExplanationPayload)
def create_unassigned_task_explanation(
    request: UnassignedTaskExplanationRequest,
    context: AuthenticatedUserContext = Depends(require_ai_layer_access),
    service: ExplanationService = Depends(get_explanation_service),
) -> AiExplanationPayload:
    """Return an advisory explanation for one unassigned planner outcome."""

    try:
        result = service.build_unassigned_explanation(
            task_id=request.task_id,
            plan_run_id=request.plan_run_id,
            user_context=context,
        )
    except ExplanationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _build_response_payload(result)
