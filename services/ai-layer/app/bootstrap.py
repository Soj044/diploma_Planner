"""Startup helpers for ai-layer runtime bootstrap.

This module keeps the startup retry loop for the shared PostgreSQL connection
and delegates AI schema/table creation plus sync-target seeding to the
repository and application layers.
"""

import time

from psycopg import Error, OperationalError, connect

from app.application.reindex import ReindexService
from app.config import (
    AI_DB_CONNECT_RETRIES,
    AI_DB_CONNECT_RETRY_DELAY_SECONDS,
    AI_VECTOR_DIM,
    CORE_SERVICE_URL,
    INTERNAL_SERVICE_TOKEN,
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_MODEL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_TIMEOUT_SECONDS,
    PLANNER_SERVICE_URL,
    postgres_dsn,
)
from app.infrastructure.clients.core_service import CoreServiceAuthClient
from app.infrastructure.clients.ollama import OllamaClient
from app.infrastructure.clients.planner_service import PlannerServiceClient
from app.infrastructure.repositories.postgres import PostgresAiRepository


def _wait_for_database_connection(dsn: str) -> None:
    """Retry the shared PostgreSQL connection until the bootstrap timeout is reached."""

    last_error: OperationalError | None = None
    for attempt in range(1, AI_DB_CONNECT_RETRIES + 1):
        try:
            with connect(dsn, autocommit=True):
                return
        except OperationalError as exc:
            last_error = exc
            if attempt == AI_DB_CONNECT_RETRIES:
                break
            time.sleep(AI_DB_CONNECT_RETRY_DELAY_SECONDS)

    raise RuntimeError(
        "Failed to connect ai-layer to PostgreSQL during startup bootstrap.",
    ) from last_error


def initialize_storage() -> None:
    """Ensure the shared PostgreSQL instance is ready for ai-layer usage."""

    dsn = postgres_dsn()
    _wait_for_database_connection(dsn)

    repository = PostgresAiRepository(dsn=dsn, vector_dim=AI_VECTOR_DIM)
    reindex_service = ReindexService(
        repository=repository,
        core_service_client=CoreServiceAuthClient(
            base_url=CORE_SERVICE_URL,
            internal_service_token=INTERNAL_SERVICE_TOKEN,
        ),
        planner_service_client=PlannerServiceClient(
            base_url=PLANNER_SERVICE_URL,
            internal_service_token=INTERNAL_SERVICE_TOKEN,
        ),
        ollama_client=OllamaClient(
            base_url=OLLAMA_BASE_URL,
            chat_model=OLLAMA_CHAT_MODEL,
            embed_model=OLLAMA_EMBED_MODEL,
            timeout_seconds=OLLAMA_TIMEOUT_SECONDS,
        ),
    )

    try:
        repository.ensure_foundation()
        reindex_service.ensure_sync_targets()
    except Error as exc:
        raise RuntimeError("Failed to initialize ai-layer PostgreSQL foundation.") from exc
