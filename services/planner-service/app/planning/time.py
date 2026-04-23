"""Time helpers for planner-service."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)
