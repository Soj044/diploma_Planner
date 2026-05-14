"""Unit tests for ai-layer retrieval sync orchestration."""

from datetime import UTC, datetime, timedelta

from app.application.reindex import ReindexService
from app.dtos import IndexFeedEnvelope
from app.infrastructure.clients.core_service import CoreServiceAiReadError
from app.infrastructure.repositories.postgres import IndexItemRecord, IndexSearchFilters, SyncStateRecord


class FakeRepository:
    """In-memory repository stand-in for reindex-service unit tests."""

    def __init__(self) -> None:
        """Prepare empty sync-state and index storage for one test case."""

        self.items: dict[tuple[str, str, str], dict[str, object]] = {}
        self.sync_state: dict[str, SyncStateRecord] = {}

    def seed_sync_targets(self, targets: list[str]) -> None:
        """Insert sync-state rows once without disturbing existing entries."""

        now = datetime.now(tz=UTC)
        for target in targets:
            self.sync_state.setdefault(
                target,
                SyncStateRecord(
                    source_service=target,
                    cursor_value=None,
                    last_source_updated_at=None,
                    last_synced_at=None,
                    updated_at=now,
                ),
            )

    def get_sync_state(self, source_service: str) -> SyncStateRecord | None:
        """Return the stored sync-state row for one source service."""

        return self.sync_state.get(source_service)

    def upsert_sync_state(
        self,
        *,
        source_service: str,
        cursor_value: str | None,
        last_source_updated_at: datetime | None,
        last_synced_at: datetime | None,
    ) -> SyncStateRecord:
        """Store one sync-state row and return the resulting typed record."""

        record = SyncStateRecord(
            source_service=source_service,
            cursor_value=cursor_value,
            last_source_updated_at=last_source_updated_at,
            last_synced_at=last_synced_at,
            updated_at=datetime.now(tz=UTC),
        )
        self.sync_state[source_service] = record
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
        """Store one indexed item by its stable source identity."""

        key = (source_service, source_type, source_key)
        created_at = self.items.get(key, {}).get("created_at", datetime.now(tz=UTC))
        payload = {
            "id": len(self.items) + 1,
            "source_service": source_service,
            "source_type": source_type,
            "source_key": source_key,
            "title": title,
            "content": content,
            "metadata_json": metadata_json,
            "source_updated_at": source_updated_at,
            "created_at": created_at,
            "updated_at": datetime.now(tz=UTC),
            "embedding": embedding,
        }
        self.items[key] = payload
        return IndexItemRecord(**{field: payload[field] for field in IndexItemRecord.__dataclass_fields__})

    def delete_index_item(self, *, source_service: str, source_type: str, source_key: str) -> int:
        """Delete one indexed item by identity and report whether it existed."""

        key = (source_service, source_type, source_key)
        if key not in self.items:
            return 0
        del self.items[key]
        return 1

    def count_index_items(self, filters: IndexSearchFilters | None = None) -> int:
        """Count indexed items that match the optional exact filters."""

        effective_filters = filters or IndexSearchFilters()
        count = 0
        for source_service, source_type, _source_key in self.items:
            if effective_filters.source_service and source_service != effective_filters.source_service:
                continue
            if effective_filters.source_type and source_type != effective_filters.source_type:
                continue
            count += 1
        return count


class FeedClient:
    """Simple sequential feed client used to stub core/planner AI feeds."""

    def __init__(self, feeds: list[IndexFeedEnvelope] | None = None, error: Exception | None = None) -> None:
        """Prepare sequential feed responses or one configured failure."""

        self.feeds = feeds or []
        self.error = error
        self.requests: list[datetime | None] = []

    def list_index_feed(self, changed_since: datetime | None) -> IndexFeedEnvelope:
        """Return the next configured feed or raise the configured upstream error."""

        self.requests.append(changed_since)
        if self.error is not None:
            raise self.error
        return self.feeds.pop(0)


class FakeOllamaClient:
    """Stub embedding client for reindex-service unit tests."""

    def __init__(self) -> None:
        """Prepare an empty request log for embedding assertions."""

        self.requests: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one deterministic embedding vector per requested text."""

        self.requests.append(texts)
        return [[0.0] * 1024 for _text in texts]


def _feed(
    *,
    source_service: str,
    source_type: str,
    source_key: str,
    index_action: str,
    source_updated_at: datetime,
) -> IndexFeedEnvelope:
    """Build one minimal typed feed envelope for reindex-service tests."""

    return IndexFeedEnvelope.model_validate(
        {
            "source_service": source_service,
            "generated_at": source_updated_at.isoformat(),
            "next_changed_since": source_updated_at.isoformat(),
            "items": [
                {
                    "source_type": source_type,
                    "source_key": source_key,
                    "index_action": index_action,
                    "title": "Indexed case",
                    "content": "Flattened retrieval body",
                    "metadata": {"kind": source_type},
                    "source_updated_at": source_updated_at.isoformat(),
                }
            ],
        }
    )


def test_reindex_all_populates_both_sources() -> None:
    """Populate both configured retrieval corpora during a full reindex cycle."""

    repository = FakeRepository()
    core_feed_client = FeedClient(
        feeds=[
            _feed(
                source_service="core-service",
                source_type="assignment_case",
                source_key="assignment:1",
                index_action="upsert",
                source_updated_at=datetime.now(tz=UTC),
            )
        ]
    )
    planner_feed_client = FeedClient(
        feeds=[
            _feed(
                source_service="planner-service",
                source_type="unassigned_case",
                source_key="unassigned:run-1:task-2",
                index_action="upsert",
                source_updated_at=datetime.now(tz=UTC),
            )
        ]
    )
    service = ReindexService(
        repository=repository,
        core_service_client=core_feed_client,  # type: ignore[arg-type]
        planner_service_client=planner_feed_client,  # type: ignore[arg-type]
        ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
    )

    results = service.reindex_all()

    assert len(results) == 2
    assert repository.count_index_items() == 2
    assert repository.get_sync_state("core-service") is not None
    assert repository.get_sync_state("planner-service") is not None


def test_refresh_source_deletes_indexed_item_when_feed_emits_delete() -> None:
    """Remove an indexed assignment case when the upstream feed switches to `delete`."""

    repository = FakeRepository()
    initial_time = datetime.now(tz=UTC) - timedelta(minutes=10)
    later_time = datetime.now(tz=UTC)
    core_feed_client = FeedClient(
        feeds=[
            _feed(
                source_service="core-service",
                source_type="assignment_case",
                source_key="assignment:1",
                index_action="upsert",
                source_updated_at=initial_time,
            ),
            _feed(
                source_service="core-service",
                source_type="assignment_case",
                source_key="assignment:1",
                index_action="delete",
                source_updated_at=later_time,
            ),
        ]
    )
    service = ReindexService(
        repository=repository,
        core_service_client=core_feed_client,  # type: ignore[arg-type]
        planner_service_client=FeedClient(),  # type: ignore[arg-type]
        ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
    )

    service.refresh_source(source_service="core-service", force_full=True)
    assert repository.count_index_items(
        IndexSearchFilters(source_service="core-service", source_type="assignment_case")
    ) == 1

    service.refresh_source(source_service="core-service", force_full=False)

    assert repository.count_index_items(
        IndexSearchFilters(source_service="core-service", source_type="assignment_case")
    ) == 0
    assert repository.get_sync_state("core-service").cursor_value == later_time.isoformat()


def test_refresh_if_stale_allows_stale_fallback_when_old_index_exists() -> None:
    """Keep serving explanations from stale index data when refresh fails but corpus exists."""

    repository = FakeRepository()
    stale_time = datetime.now(tz=UTC) - timedelta(minutes=30)
    repository.seed_sync_targets(["core-service", "planner-service"])
    repository.upsert_sync_state(
        source_service="core-service",
        cursor_value=stale_time.isoformat(),
        last_source_updated_at=stale_time,
        last_synced_at=stale_time,
    )
    repository.upsert_index_item(
        source_service="core-service",
        source_type="assignment_case",
        source_key="assignment:1",
        title="Existing case",
        content="Derived assignment case",
        metadata_json={"kind": "assignment_case"},
        source_updated_at=stale_time,
        embedding=[0.0] * 1024,
    )
    service = ReindexService(
        repository=repository,
        core_service_client=FeedClient(
            error=CoreServiceAiReadError(
                status_code=503,
                detail="core-service internal AI index feed is unavailable",
            )
        ),  # type: ignore[arg-type]
        planner_service_client=FeedClient(),  # type: ignore[arg-type]
        ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
    )

    stale_sources = service.refresh_if_stale(["core-service"])

    assert stale_sources == {"core-service"}
