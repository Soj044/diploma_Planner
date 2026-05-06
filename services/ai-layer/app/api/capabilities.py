"""Frontend-facing ai-layer capability routes.

This module exposes the first authenticated ai-layer endpoint. It applies the
same Bearer introspection pattern as planner-service and returns a minimal,
non-generative response that frontend code can use to verify auth wiring and
configured AI runtime metadata.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import (
    AI_TOP_K,
    AI_VECTOR_DIM,
    CORE_SERVICE_URL,
    INTERNAL_SERVICE_TOKEN,
    OLLAMA_CHAT_MODEL,
    OLLAMA_EMBED_MODEL,
)
from app.infrastructure.clients.core_service import (
    AuthenticatedUserContext,
    CoreServiceAuthClient,
    CoreServiceAuthError,
)

router = APIRouter(prefix="/api/v1", tags=["capabilities"])
auth_client = CoreServiceAuthClient(
    base_url=CORE_SERVICE_URL,
    internal_service_token=INTERNAL_SERVICE_TOKEN,
)
ALLOWED_AI_ROLES = {"admin", "manager"}


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


def require_ai_layer_access(authorization: str | None = Header(default=None)) -> AuthenticatedUserContext:
    """Allow ai-layer access only for active admin and manager users."""

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Bearer access token is required.")

    try:
        context = auth_client.introspect_access_token(token.strip())
    except CoreServiceAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if not context.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive.")
    if context.role not in ALLOWED_AI_ROLES:
        raise HTTPException(status_code=403, detail="You do not have access to ai-layer.")
    return context


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
