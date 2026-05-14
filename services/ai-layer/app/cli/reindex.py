"""CLI entrypoint for ai-layer retrieval index refresh operations.

This module allows local operators and automated checks to trigger a full
refresh of the derived retrieval corpus without starting the HTTP server.
"""

from __future__ import annotations

import argparse

from app.application.reindex import DEFAULT_SYNC_TARGETS, ReindexService
from app.config import (
    AI_VECTOR_DIM,
    CORE_SERVICE_URL,
    INTERNAL_SERVICE_TOKEN,
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_MODEL,
    OLLAMA_EMBED_MODEL,
    PLANNER_SERVICE_URL,
    postgres_dsn,
)
from app.infrastructure.clients.core_service import CoreServiceAuthClient
from app.infrastructure.clients.ollama import OllamaClient
from app.infrastructure.clients.planner_service import PlannerServiceClient
from app.infrastructure.repositories.postgres import PostgresAiRepository


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for full ai-layer reindex operations."""

    parser = argparse.ArgumentParser(description="Refresh ai-layer retrieval index data.")
    parser.add_argument(
        "--mode",
        choices=("full",),
        default="full",
        help="Refresh mode to execute. Only full reindex is supported in this cycle.",
    )
    parser.add_argument(
        "--source",
        choices=DEFAULT_SYNC_TARGETS,
        default=None,
        help="Optional single source to reindex instead of all configured sources.",
    )
    return parser.parse_args()


def build_reindex_service() -> ReindexService:
    """Build the reindex service graph used by the standalone CLI entrypoint."""

    repository = PostgresAiRepository(dsn=postgres_dsn(), vector_dim=AI_VECTOR_DIM)
    repository.ensure_foundation()
    return ReindexService(
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
        ),
    )


def main() -> int:
    """Run the requested ai-layer reindex command and return a shell exit code."""

    args = parse_args()
    service = build_reindex_service()
    service.ensure_sync_targets()
    targets = [args.source] if args.source else list(DEFAULT_SYNC_TARGETS)
    service.reindex_all(targets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
