"""Typed internal DTOs for ai-layer sync and explanation flows.

This module keeps ai-layer-only data transfer objects close to the service that
consumes them. They validate internal feed/context payloads from core-service
and planner-service, plus the structured explanation output expected from the
local Ollama runtime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IndexFeedItem(BaseModel):
    """One flattened retrieval item emitted by an upstream internal AI feed."""

    source_type: str
    source_key: str
    index_action: Literal["upsert", "delete"]
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_updated_at: datetime


class IndexFeedEnvelope(BaseModel):
    """One internal AI index-feed page for a single source service."""

    source_service: str
    generated_at: datetime
    next_changed_since: datetime
    items: list[IndexFeedItem] = Field(default_factory=list)


class AssignmentLiveContext(BaseModel):
    """Live task-plus-employee context fetched from core-service."""

    task: dict[str, Any]
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    employee: dict[str, Any]
    employee_skills: list[dict[str, Any]] = Field(default_factory=list)
    availability: dict[str, Any]


class ProposalContext(BaseModel):
    """Persisted planner proposal context fetched from planner-service."""

    plan_run_summary: dict[str, Any]
    task_snapshot: dict[str, Any]
    proposal: dict[str, Any]
    sibling_proposals: list[dict[str, Any]] = Field(default_factory=list)
    eligibility: dict[str, Any]
    score_map: dict[str, float] = Field(default_factory=dict)
    solver_summary: dict[str, Any] = Field(default_factory=dict)


class UnassignedContext(BaseModel):
    """Persisted planner diagnostic context fetched from planner-service."""

    plan_run_summary: dict[str, Any]
    task_snapshot: dict[str, Any]
    diagnostic: dict[str, Any]
    eligibility: dict[str, Any]
    score_map: dict[str, float] = Field(default_factory=dict)
    solver_summary: dict[str, Any] = Field(default_factory=dict)


class StructuredExplanationOutput(BaseModel):
    """Strict LLM output schema used before ai-layer adds similar-case metadata."""

    summary: str
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    advisory_note: str
