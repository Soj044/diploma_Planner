"""PostgreSQL repository for ai-layer derived storage.

This module owns raw `psycopg` access to the `ai_layer` schema. It creates the
foundation tables for retrieval and explanation logs and exposes typed
operations that the application layer can build on without introducing an ORM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from psycopg import connect
from psycopg.rows import class_row


@dataclass(frozen=True)
class IndexItemRecord:
    """Stored AI retrieval item persisted in the shared PostgreSQL instance."""

    id: int
    source_service: str
    source_type: str
    source_key: str
    title: str
    content: str
    metadata_json: dict[str, object]
    source_updated_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RetrievedIndexItem:
    """Stored AI retrieval item plus similarity distance from one vector search."""

    id: int
    source_service: str
    source_type: str
    source_key: str
    title: str
    content: str
    metadata_json: dict[str, object]
    source_updated_at: datetime
    created_at: datetime
    updated_at: datetime
    distance: float


@dataclass(frozen=True)
class SyncStateRecord:
    """Per-source sync cursor and freshness metadata for ai-layer indexing."""

    source_service: str
    cursor_value: str | None
    last_source_updated_at: datetime | None
    last_synced_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True)
class IndexSearchFilters:
    """Optional exact-match filters applied before vector similarity ordering."""

    source_service: str | None = None
    source_type: str | None = None


class PostgresAiRepository:
    """Persist and query ai-layer retrieval and explanation data in PostgreSQL."""

    def __init__(self, dsn: str, vector_dim: int) -> None:
        """Store the shared PostgreSQL DSN and expected embedding dimension."""

        self._dsn = dsn
        self._vector_dim = vector_dim

    def ensure_foundation(self) -> None:
        """Create the ai-layer schema, extension, tables, and vector index if missing."""

        with connect(self._dsn, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cursor.execute("CREATE SCHEMA IF NOT EXISTS ai_layer;")
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS ai_layer.index_items (
                        id bigserial PRIMARY KEY,
                        source_service text NOT NULL,
                        source_type text NOT NULL,
                        source_key text NOT NULL,
                        title text NOT NULL,
                        content text NOT NULL,
                        metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                        source_updated_at timestamptz NOT NULL,
                        embedding vector({self._vector_dim}) NOT NULL,
                        created_at timestamptz NOT NULL DEFAULT now(),
                        updated_at timestamptz NOT NULL DEFAULT now(),
                        CONSTRAINT ai_layer_index_items_source_identity_key
                            UNIQUE (source_service, source_type, source_key)
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_layer.sync_state (
                        source_service text PRIMARY KEY,
                        cursor_value text NULL,
                        last_source_updated_at timestamptz NULL,
                        last_synced_at timestamptz NULL,
                        updated_at timestamptz NOT NULL DEFAULT now()
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_layer.explanation_logs (
                        id bigserial PRIMARY KEY,
                        request_type text NOT NULL,
                        user_id bigint NOT NULL,
                        request_json jsonb NOT NULL,
                        retrieved_keys_json jsonb NOT NULL DEFAULT '[]'::jsonb,
                        response_json jsonb NULL,
                        model_name text NOT NULL,
                        created_at timestamptz NOT NULL DEFAULT now()
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS ai_layer_index_items_embedding_hnsw_idx
                    ON ai_layer.index_items USING hnsw (embedding vector_cosine_ops);
                    """
                )

    def seed_sync_targets(self, targets: list[str]) -> None:
        """Insert the required sync targets once without disturbing existing rows."""

        with connect(self._dsn, autocommit=True) as connection:
            with connection.cursor() as cursor:
                for target in targets:
                    cursor.execute(
                        """
                        INSERT INTO ai_layer.sync_state (source_service)
                        VALUES (%s)
                        ON CONFLICT (source_service) DO NOTHING;
                        """,
                        (target,),
                    )

    def get_sync_state(self, source_service: str) -> SyncStateRecord | None:
        """Return one sync-state row for the requested upstream source service."""

        with connect(self._dsn, autocommit=True, row_factory=class_row(SyncStateRecord)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT source_service, cursor_value, last_source_updated_at, last_synced_at, updated_at
                    FROM ai_layer.sync_state
                    WHERE source_service = %s;
                    """,
                    (source_service,),
                )
                return cursor.fetchone()

    def upsert_sync_state(
        self,
        *,
        source_service: str,
        cursor_value: str | None,
        last_source_updated_at: datetime | None,
        last_synced_at: datetime | None,
    ) -> SyncStateRecord:
        """Insert or update one sync-state row and return the stored record."""

        with connect(self._dsn, autocommit=True, row_factory=class_row(SyncStateRecord)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_layer.sync_state (
                        source_service,
                        cursor_value,
                        last_source_updated_at,
                        last_synced_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, now())
                    ON CONFLICT (source_service) DO UPDATE
                    SET cursor_value = EXCLUDED.cursor_value,
                        last_source_updated_at = EXCLUDED.last_source_updated_at,
                        last_synced_at = EXCLUDED.last_synced_at,
                        updated_at = now()
                    RETURNING source_service, cursor_value, last_source_updated_at, last_synced_at, updated_at;
                    """,
                    (source_service, cursor_value, last_source_updated_at, last_synced_at),
                )
                record = cursor.fetchone()
        assert record is not None
        return record

    def upsert_index_item(
        self,
        *,
        source_service: str,
        source_type: str,
        source_key: str,
        title: str,
        content: str,
        metadata_json: dict[str, object],
        source_updated_at: datetime,
        embedding: list[float],
    ) -> IndexItemRecord:
        """Insert or update one retrieval index row and return the stored record."""

        embedding_literal = self._format_vector_literal(embedding)
        with connect(self._dsn, autocommit=True, row_factory=class_row(IndexItemRecord)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_layer.index_items (
                        source_service,
                        source_type,
                        source_key,
                        title,
                        content,
                        metadata_json,
                        source_updated_at,
                        embedding,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::vector, now())
                    ON CONFLICT (source_service, source_type, source_key) DO UPDATE
                    SET title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        metadata_json = EXCLUDED.metadata_json,
                        source_updated_at = EXCLUDED.source_updated_at,
                        embedding = EXCLUDED.embedding,
                        updated_at = now()
                    RETURNING id, source_service, source_type, source_key, title, content, metadata_json,
                              source_updated_at, created_at, updated_at;
                    """,
                    (
                        source_service,
                        source_type,
                        source_key,
                        title,
                        content,
                        self._dumps_json(metadata_json),
                        source_updated_at,
                        embedding_literal,
                    ),
                )
                record = cursor.fetchone()
        assert record is not None
        return record

    def count_index_items(self) -> int:
        """Return the number of retrieval items currently stored in ai-layer."""

        with connect(self._dsn, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM ai_layer.index_items;")
                row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def search_similar_items(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: IndexSearchFilters | None = None,
    ) -> list[RetrievedIndexItem]:
        """Run cosine similarity search over stored retrieval items."""

        if top_k <= 0:
            return []

        embedding_literal = self._format_vector_literal(query_embedding)
        effective_filters = filters or IndexSearchFilters()

        conditions: list[str] = []
        parameters: list[object] = []
        if effective_filters.source_service:
            conditions.append("source_service = %s")
            parameters.append(effective_filters.source_service)
        if effective_filters.source_type:
            conditions.append("source_type = %s")
            parameters.append(effective_filters.source_type)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT id, source_service, source_type, source_key, title, content, metadata_json,
                   source_updated_at, created_at, updated_at,
                   embedding <=> %s::vector AS distance
            FROM ai_layer.index_items
            {where_clause}
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        with connect(self._dsn, autocommit=True, row_factory=class_row(RetrievedIndexItem)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, [embedding_literal, *parameters, embedding_literal, top_k])
                records = cursor.fetchall()
        return list(records)

    def insert_explanation_log(
        self,
        *,
        request_type: str,
        user_id: int,
        request_json: dict[str, object],
        retrieved_keys_json: list[str],
        response_json: dict[str, object] | None,
        model_name: str,
    ) -> int:
        """Persist one explanation run audit row and return its database identifier."""

        with connect(self._dsn, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_layer.explanation_logs (
                        request_type,
                        user_id,
                        request_json,
                        retrieved_keys_json,
                        response_json,
                        model_name
                    )
                    VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                    RETURNING id;
                    """,
                    (
                        request_type,
                        user_id,
                        self._dumps_json(request_json),
                        self._dumps_json(retrieved_keys_json),
                        self._dumps_json(response_json) if response_json is not None else None,
                        model_name,
                    ),
                )
                row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def _format_vector_literal(self, embedding: list[float]) -> str:
        """Convert an embedding into a PostgreSQL vector literal after validation."""

        if len(embedding) != self._vector_dim:
            raise ValueError(
                f"Expected embedding of size {self._vector_dim}, received {len(embedding)}.",
            )
        return "[" + ",".join(f"{value:.12g}" for value in embedding) + "]"

    def _dumps_json(self, value: object) -> str:
        """Serialize Python data into a stable JSON string for PostgreSQL casts."""

        return json.dumps(value, separators=(",", ":"), sort_keys=True)
