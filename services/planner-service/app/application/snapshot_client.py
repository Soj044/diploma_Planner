"""Snapshot client boundary for planner orchestration."""

from typing import Protocol

from contracts.schemas import CreatePlanRunRequest, PlanningSnapshot


class SnapshotClientError(Exception):
    """Raised when planner-service cannot fetch a planning snapshot."""


class SnapshotClient(Protocol):
    """Fetch planning snapshots from core-service."""

    def fetch_snapshot(self, request: CreatePlanRunRequest) -> PlanningSnapshot:
        """Return a validated planning snapshot for the requested planning window."""
