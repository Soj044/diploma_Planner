"""Application helpers for ai-layer retrieval index lifecycle.

This module owns ai-layer sync semantics for derived retrieval data. It seeds
required source rows, performs full or incremental feed refreshes, updates sync
state, and exposes the stale-refresh fallback used before public explanations.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.config import AI_SYNC_STALE_SECONDS
from app.dtos import IndexFeedEnvelope, IndexFeedItem
from app.infrastructure.clients.core_service import CoreServiceAiReadError, CoreServiceAuthClient
from app.infrastructure.clients.ollama import OllamaClient, OllamaClientError
from app.infrastructure.clients.planner_service import PlannerServiceAiReadError, PlannerServiceClient
from app.infrastructure.repositories.postgres import IndexSearchFilters, PostgresAiRepository

DEFAULT_SYNC_TARGETS: tuple[str, ...] = ("core-service", "planner-service")
SOURCE_TYPES_BY_SERVICE = {
    "core-service": "assignment_case",
    "planner-service": "unassigned_case",
}


class ReindexServiceError(Exception):
    """Raised when ai-layer cannot refresh retrieval data for one upstream source."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        """Store the stable HTTP-style status and detail for the failed refresh."""

        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class SyncRefreshResult:
    """Outcome of one source refresh attempt during AI sync orchestration."""

    source_service: str
    refreshed: bool
    used_cursor: str | None
    next_cursor: str


class ReindexService:
    """Manage ai-layer retrieval sync state and source refresh behavior."""

    def __init__(
        self,
        repository: PostgresAiRepository,
        core_service_client: CoreServiceAuthClient,
        planner_service_client: PlannerServiceClient,
        ollama_client: OllamaClient,
        sync_targets: Sequence[str] = DEFAULT_SYNC_TARGETS,
        stale_seconds: int = AI_SYNC_STALE_SECONDS,
    ) -> None:
        """Bind storage and upstream clients used for full and incremental refresh."""

        self._repository = repository
        self._core_service_client = core_service_client
        self._planner_service_client = planner_service_client
        self._ollama_client = ollama_client
        self._sync_targets = tuple(sync_targets)
        self._stale_seconds = stale_seconds

    def ensure_sync_targets(self) -> None:
        """Seed the required sync targets without duplicating existing rows."""

        self._repository.seed_sync_targets(list(self._sync_targets))

    def is_index_ready(
        self,
        *,
        source_service: str | None = None,
        source_type: str | None = None,
    ) -> bool:
        """Return whether the requested retrieval slice has sync state and indexed rows."""

        filters = IndexSearchFilters(
            source_service=source_service,
            source_type=source_type,
        )
        if self._repository.count_index_items(filters) == 0:
            return False
        if source_service is not None:
            return self._repository.get_sync_state(source_service) is not None
        return all(self._repository.get_sync_state(target) is not None for target in self._sync_targets)

    def reindex_all(self, source_services: Sequence[str] | None = None) -> list[SyncRefreshResult]:
        """Perform a full reindex for one or more configured upstream sources."""

        self.ensure_sync_targets()
        targets = tuple(source_services or self._sync_targets)
        return [self.refresh_source(source_service=target, force_full=True) for target in targets]

    def refresh_source(
        self,
        *,
        source_service: str,
        force_full: bool = False,
    ) -> SyncRefreshResult:
        """Refresh one upstream retrieval source through its internal AI feed."""

        self.ensure_sync_targets()
        sync_state = self._repository.get_sync_state(source_service)
        used_cursor = None if force_full or sync_state is None else sync_state.cursor_value
        changed_since = self._parse_cursor(used_cursor) if used_cursor else None

        try:
            feed = self._fetch_feed(source_service, changed_since)
            if feed.source_service != source_service:
                raise ReindexServiceError(
                    status_code=502,
                    detail="Internal AI index feed returned an unexpected source_service value.",
                )
            self._apply_feed(feed)
        except (CoreServiceAiReadError, PlannerServiceAiReadError, OllamaClientError) as exc:
            raise ReindexServiceError(status_code=exc.status_code, detail=exc.detail) from exc

        last_source_updated_at = (
            max((item.source_updated_at for item in feed.items), default=None)
            or (sync_state.last_source_updated_at if sync_state is not None else None)
        )
        self._repository.upsert_sync_state(
            source_service=source_service,
            cursor_value=feed.next_changed_since.isoformat(),
            last_source_updated_at=last_source_updated_at,
            last_synced_at=datetime.now(tz=UTC),
        )
        return SyncRefreshResult(
            source_service=source_service,
            refreshed=True,
            used_cursor=used_cursor,
            next_cursor=feed.next_changed_since.isoformat(),
        )

    def refresh_if_stale(self, source_services: Sequence[str]) -> set[str]:
        """Refresh stale sources and report which ones fell back to stale index data."""

        stale_sources: set[str] = set()
        self.ensure_sync_targets()
        now = datetime.now(tz=UTC)

        for source_service in source_services:
            sync_state = self._repository.get_sync_state(source_service)
            if sync_state is not None and sync_state.last_synced_at is not None:
                age_seconds = (now - sync_state.last_synced_at).total_seconds()
                if age_seconds <= self._stale_seconds:
                    continue

            try:
                self.refresh_source(source_service=source_service, force_full=False)
            except ReindexServiceError as exc:
                source_type = SOURCE_TYPES_BY_SERVICE.get(source_service)
                if source_type and self.is_index_ready(source_service=source_service, source_type=source_type):
                    stale_sources.add(source_service)
                    continue
                raise exc

        return stale_sources

    def _fetch_feed(
        self,
        source_service: str,
        changed_since: datetime | None,
    ) -> IndexFeedEnvelope:
        """Dispatch one incremental feed read to the correct upstream service client."""

        if source_service == "core-service":
            return self._core_service_client.list_index_feed(changed_since)
        if source_service == "planner-service":
            return self._planner_service_client.list_index_feed(changed_since)
        raise ReindexServiceError(status_code=503, detail=f"Unknown AI sync source '{source_service}'.")

    def _apply_feed(self, feed: IndexFeedEnvelope) -> None:
        """Apply one feed envelope by deleting or upserting retrieval records."""

        upsert_items = [item for item in feed.items if item.index_action == "upsert"]
        embeddings = self._embed_index_items(upsert_items)

        for item in feed.items:
            if item.index_action == "delete":
                self._repository.delete_index_item(
                    source_service=feed.source_service,
                    source_type=item.source_type,
                    source_key=item.source_key,
                )

        for item, embedding in zip(upsert_items, embeddings, strict=True):
            self._repository.upsert_index_item(
                source_service=feed.source_service,
                source_type=item.source_type,
                source_key=item.source_key,
                title=item.title,
                content=item.content,
                metadata_json=item.metadata,
                source_updated_at=item.source_updated_at,
                embedding=embedding,
            )

    def _embed_index_items(self, items: list[IndexFeedItem]) -> list[list[float]]:
        """Embed all upsert feed items before they are written to pgvector storage."""

        if not items:
            return []
        embeddings = self._ollama_client.embed_texts([self._embedding_text(item) for item in items])
        if len(embeddings) != len(items):
            raise ReindexServiceError(
                status_code=502,
                detail="ollama embedding payload size does not match the AI index feed batch",
            )
        return embeddings

    def _embedding_text(self, item: IndexFeedItem) -> str:
        """Build the text representation that ai-layer stores as one vector embedding."""

        return f"{item.title}\n\n{item.content}"

    def _parse_cursor(self, raw_cursor: str) -> datetime:
        """Parse one previously stored sync cursor into a timezone-aware datetime."""

        try:
            parsed = datetime.fromisoformat(raw_cursor)
        except ValueError as exc:
            raise ReindexServiceError(status_code=503, detail="Stored AI sync cursor is invalid.") from exc
        if parsed.tzinfo is None:
            raise ReindexServiceError(status_code=503, detail="Stored AI sync cursor is invalid.")
        return parsed
