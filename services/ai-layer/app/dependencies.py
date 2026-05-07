"""Shared dependency providers for ai-layer routes.

This module centralizes runtime clients, repository instances, and access
control helpers so capability and explanation routes reuse the same service
graph and Bearer-introspection policy.
"""

from functools import lru_cache

from fastapi import Depends, Header, HTTPException

from app.application.explanations import ExplanationService
from app.application.reindex import ReindexService
from app.config import (
    AI_TOP_K,
    AI_VECTOR_DIM,
    CORE_SERVICE_URL,
    INTERNAL_SERVICE_TOKEN,
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_MODEL,
    OLLAMA_EMBED_MODEL,
    PLANNER_SERVICE_URL,
    postgres_dsn,
)
from app.infrastructure.clients.core_service import (
    AuthenticatedUserContext,
    CoreServiceAuthClient,
    CoreServiceAuthError,
)
from app.infrastructure.clients.ollama import OllamaClient
from app.infrastructure.clients.planner_service import PlannerServiceClient
from app.infrastructure.repositories.postgres import PostgresAiRepository

ALLOWED_AI_ROLES = {"admin", "manager"}


def _extract_bearer_token(authorization: str | None) -> str:
    """Validate the Authorization header and return the contained Bearer token."""

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Bearer access token is required.")
    return token.strip()


@lru_cache
def get_ai_repository() -> PostgresAiRepository:
    """Return the shared PostgreSQL repository for derived ai-layer storage."""

    return PostgresAiRepository(dsn=postgres_dsn(), vector_dim=AI_VECTOR_DIM)


@lru_cache
def get_core_service_client() -> CoreServiceAuthClient:
    """Return the shared core-service client for auth and future internal reads."""

    return CoreServiceAuthClient(
        base_url=CORE_SERVICE_URL,
        internal_service_token=INTERNAL_SERVICE_TOKEN,
    )


@lru_cache
def get_planner_service_client() -> PlannerServiceClient:
    """Return the shared planner-service client for future internal AI reads."""

    return PlannerServiceClient(
        base_url=PLANNER_SERVICE_URL,
        internal_service_token=INTERNAL_SERVICE_TOKEN,
    )


@lru_cache
def get_ollama_client() -> OllamaClient:
    """Return the shared Ollama client for embeddings and future generation."""

    return OllamaClient(
        base_url=OLLAMA_BASE_URL,
        chat_model=OLLAMA_CHAT_MODEL,
        embed_model=OLLAMA_EMBED_MODEL,
    )


def get_reindex_service(
    repository: PostgresAiRepository = Depends(get_ai_repository),
    core_service_client: CoreServiceAuthClient = Depends(get_core_service_client),
    planner_service_client: PlannerServiceClient = Depends(get_planner_service_client),
    ollama_client: OllamaClient = Depends(get_ollama_client),
) -> ReindexService:
    """Return the application helper that owns index readiness state."""

    return ReindexService(
        repository=repository,
        core_service_client=core_service_client,
        planner_service_client=planner_service_client,
        ollama_client=ollama_client,
    )


def get_explanation_service(
    repository: PostgresAiRepository = Depends(get_ai_repository),
    reindex_service: ReindexService = Depends(get_reindex_service),
    core_service_client: CoreServiceAuthClient = Depends(get_core_service_client),
    planner_service_client: PlannerServiceClient = Depends(get_planner_service_client),
    ollama_client: OllamaClient = Depends(get_ollama_client),
) -> ExplanationService:
    """Return the public explanation service wired to storage and runtime clients."""

    return ExplanationService(
        repository=repository,
        reindex_service=reindex_service,
        core_service_client=core_service_client,
        planner_service_client=planner_service_client,
        ollama_client=ollama_client,
        top_k=AI_TOP_K,
        model_name=OLLAMA_CHAT_MODEL,
    )


def require_ai_layer_access(
    authorization: str | None = Header(default=None),
    auth_client: CoreServiceAuthClient = Depends(get_core_service_client),
) -> AuthenticatedUserContext:
    """Allow ai-layer access only for active admin and manager users."""

    access_token = _extract_bearer_token(authorization)

    try:
        context = auth_client.introspect_access_token(access_token)
    except CoreServiceAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if not context.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive.")
    if context.role not in ALLOWED_AI_ROLES:
        raise HTTPException(status_code=403, detail="You do not have access to ai-layer.")
    return context
