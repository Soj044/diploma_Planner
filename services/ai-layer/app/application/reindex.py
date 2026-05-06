"""Application helpers for AI retrieval index lifecycle.

This module owns the minimal index-readiness rules for the current cycle. It
seeds sync targets for the services that will later feed derived AI data and
exposes a readiness check that public explanation endpoints can rely on.
"""

from collections.abc import Sequence

from app.infrastructure.repositories.postgres import PostgresAiRepository

DEFAULT_SYNC_TARGETS: tuple[str, ...] = ("core-service", "planner-service")


class ReindexService:
    """Manage the current-cycle readiness state of the AI retrieval index."""

    def __init__(
        self,
        repository: PostgresAiRepository,
        sync_targets: Sequence[str] = DEFAULT_SYNC_TARGETS,
    ) -> None:
        """Bind the reindex service to one repository and the required sync targets."""

        self._repository = repository
        self._sync_targets = tuple(sync_targets)

    def ensure_sync_targets(self) -> None:
        """Seed the required sync targets without duplicating existing rows."""

        self._repository.seed_sync_targets(list(self._sync_targets))

    def is_index_ready(self) -> bool:
        """Return whether the AI index has both baseline sync rows and indexed items."""

        if self._repository.count_index_items() == 0:
            return False
        return all(self._repository.get_sync_state(target) is not None for target in self._sync_targets)

    def reindex_all(self) -> None:
        """Reserve a stable API for future full-reindex orchestration work."""

        raise NotImplementedError("Full AI reindex will be implemented in the next cycle.")
