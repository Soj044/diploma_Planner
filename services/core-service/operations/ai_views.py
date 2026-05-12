"""Internal AI helper endpoints for core-service.

This file exposes token-protected read-only endpoints for ai-layer integration.
They document the ownership boundary, provide flattened retrieval feed items,
and return live task-plus-employee context without exposing browser-facing auth.
"""

from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import HasInternalServiceToken

from .ai_payloads import build_assignment_context, build_assignment_index_feed


def _parse_changed_since(raw_changed_since: str | None) -> datetime | None:
    """Parse one optional UTC ISO8601 cursor used by ai-layer incremental sync."""

    if raw_changed_since is None or not raw_changed_since.strip():
        return None
    parsed = parse_datetime(raw_changed_since)
    if parsed is None:
        raise ValueError("changed_since must be a valid UTC ISO8601 datetime.")
    if timezone.is_naive(parsed):
        raise ValueError("changed_since must include an explicit UTC offset.")
    return parsed


def _parse_employee_id(raw_employee_id: str | None) -> int:
    """Parse the required employee identifier for live assignment context reads."""

    if raw_employee_id is None or not raw_employee_id.strip():
        raise ValueError("employee_id query parameter is required.")
    try:
        return int(raw_employee_id)
    except ValueError as exc:
        raise ValueError("employee_id must be an integer.") from exc


def _parse_comparison_employee_ids(raw_value: str | None) -> list[int]:
    """Parse an optional comma-separated list of comparison employee identifiers."""

    if raw_value is None or not raw_value.strip():
        return []
    parsed_ids: list[int] = []
    for raw_item in raw_value.split(","):
        value = raw_item.strip()
        if not value:
            continue
        try:
            parsed_ids.append(int(value))
        except ValueError as exc:
            raise ValueError("comparison_employee_ids must contain only integers.") from exc
    return parsed_ids


class InternalAiServiceBoundaryView(APIView):
    """Expose the core-service ownership boundary for trusted internal AI calls."""

    permission_classes = [HasInternalServiceToken]

    def get(self, request):
        """Return a compact description of the business-truth boundary."""

        return Response(
            {
                "service": "core-service",
                "responsibility": "business truth",
                "owns": [
                    "users",
                    "employees",
                    "departments",
                    "skills",
                    "schedules",
                    "leaves",
                    "tasks",
                    "final assignments",
                ],
            }
        )


class InternalAiIndexFeedView(APIView):
    """Return the flattened `assignment_case` feed for ai-layer retrieval sync."""

    permission_classes = [HasInternalServiceToken]

    def get(self, request):
        """Build feed items filtered by the optional incremental cursor."""

        try:
            changed_since = _parse_changed_since(request.query_params.get("changed_since"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(build_assignment_index_feed(changed_since), status=status.HTTP_200_OK)


class InternalAiAssignmentContextView(APIView):
    """Return the live task-plus-employee context for assignment explanations."""

    permission_classes = [HasInternalServiceToken]

    def get(self, request, task_id: int):
        """Build the current task/employee context used by ai-layer prompts."""

        try:
            employee_id = _parse_employee_id(request.query_params.get("employee_id"))
            comparison_employee_ids = _parse_comparison_employee_ids(
                request.query_params.get("comparison_employee_ids")
            )
            payload = build_assignment_context(
                task_id=task_id,
                employee_id=employee_id,
                comparison_employee_ids=comparison_employee_ids,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return Response({"detail": "Task or employee was not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(payload, status=status.HTTP_200_OK)
