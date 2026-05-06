"""Frontend-facing ai-layer capability routes.

This module exposes authenticated runtime metadata for the browser and reuses
the shared ai-layer dependency providers so capability checks and future
explanation endpoints follow one access-control style.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import (
    AI_TOP_K,
    AI_VECTOR_DIM,
    OLLAMA_CHAT_MODEL,
    OLLAMA_EMBED_MODEL,
)
from app.dependencies import require_ai_layer_access
from app.infrastructure.clients.core_service import AuthenticatedUserContext

router = APIRouter(prefix="/api/v1", tags=["capabilities"])


class CapabilityUserPayload(BaseModel):
    """Compact authenticated user context returned by ai-layer capability checks."""

    user_id: int
    role: str
    employee_id: int | None


class AiLayerCapabilityPayload(BaseModel):
    """Response model for the authenticated ai-layer capability endpoint."""

    service: str
    responsibility: str
    chat_model: str
    embed_model: str
    vector_dim: int
    top_k: int
    user: CapabilityUserPayload


@router.get("/capabilities", response_model=AiLayerCapabilityPayload)
def get_capabilities(
    context: AuthenticatedUserContext = Depends(require_ai_layer_access),
) -> AiLayerCapabilityPayload:
    """Return the authenticated ai-layer capability baseline for frontend wiring."""

    return AiLayerCapabilityPayload(
        service="ai-layer",
        responsibility="retrieval index, explanations, and sync metadata only",
        chat_model=OLLAMA_CHAT_MODEL,
        embed_model=OLLAMA_EMBED_MODEL,
        vector_dim=AI_VECTOR_DIM,
        top_k=AI_TOP_K,
        user=CapabilityUserPayload(
            user_id=context.user_id,
            role=context.role,
            employee_id=context.employee_id,
        ),
    )
