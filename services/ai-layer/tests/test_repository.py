"""Integration tests for the ai-layer PostgreSQL repository."""

from datetime import UTC, datetime
import os
from uuid import uuid4

from psycopg import OperationalError, connect
import pytest

from app.config import AI_VECTOR_DIM, postgres_dsn
from app.infrastructure.repositories.postgres import PostgresAiRepository


def _build_test_dsn() -> str:
    """Resolve the PostgreSQL DSN used by repository integration tests."""

    return os.getenv("AI_LAYER_TEST_DSN", postgres_dsn())


def _embedding(seed: float) -> list[float]:
    """Build one repository-compatible embedding vector for pgvector tests."""

    values = [0.0] * AI_VECTOR_DIM
    values[0] = seed
    return values


@pytest.fixture(scope="module")
def repository() -> PostgresAiRepository:
    """Return a repository bound to a reachable pgvector-enabled PostgreSQL instance."""

    repository = PostgresAiRepository(dsn=_build_test_dsn(), vector_dim=AI_VECTOR_DIM)
    try:
        repository.ensure_foundation()
    except OperationalError:
        pytest.skip("pgvector PostgreSQL is not reachable for ai-layer repository tests")
    return repository


def test_ensure_foundation_is_idempotent(repository: PostgresAiRepository) -> None:
    """Allow repeated bootstrap calls without breaking the ai-layer schema foundation."""

    repository.ensure_foundation()
    repository.ensure_foundation()

    with connect(_build_test_dsn(), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'ai_layer' AND table_name = 'index_items'
                );
                """
            )
            row = cursor.fetchone()
    assert row is not None
    assert row[0] is True


def test_upsert_index_item_honors_unique_constraint(repository: PostgresAiRepository) -> None:
    """Store one logical retrieval item even when the same identity is upserted twice."""

    source_key = f"repo-test-{uuid4()}"
    source_updated_at = datetime.now(tz=UTC)

    first = repository.upsert_index_item(
        source_service="core-service",
        source_type="assignment_case",
        source_key=source_key,
        title="First title",
        content="Initial content",
        metadata_json={"version": 1},
        source_updated_at=source_updated_at,
        embedding=_embedding(0.1),
    )
    second = repository.upsert_index_item(
        source_service="core-service",
        source_type="assignment_case",
        source_key=source_key,
        title="Updated title",
        content="Updated content",
        metadata_json={"version": 2},
        source_updated_at=source_updated_at,
        embedding=_embedding(0.2),
    )

    assert first.id == second.id
    assert second.title == "Updated title"
    assert second.metadata_json == {"version": 2}


def test_hnsw_index_exists_after_foundation(repository: PostgresAiRepository) -> None:
    """Create the expected HNSW cosine index for vector similarity queries."""

    repository.ensure_foundation()

    with connect(_build_test_dsn(), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'ai_layer'
                  AND indexname = 'ai_layer_index_items_embedding_hnsw_idx';
                """
            )
            row = cursor.fetchone()

    assert row is not None
    assert "USING hnsw" in row[0]
    assert "vector_cosine_ops" in row[0]


def test_seed_sync_targets_does_not_duplicate_rows(repository: PostgresAiRepository) -> None:
    """Insert one row per required sync target even across repeated bootstrap calls."""

    repository.seed_sync_targets(["core-service", "planner-service"])
    repository.seed_sync_targets(["core-service", "planner-service"])

    with connect(_build_test_dsn(), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM ai_layer.sync_state
                WHERE source_service IN ('core-service', 'planner-service');
                """
            )
            row = cursor.fetchone()

    assert row is not None
    assert int(row[0]) == 2
