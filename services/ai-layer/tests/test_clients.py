"""Unit tests for ai-layer HTTP clients."""

import httpx
import pytest

from app.infrastructure.clients.core_service import (
    CoreServiceAiReadError,
    CoreServiceAuthClient,
    CoreServiceAuthError,
    CoreServiceBoundaryError,
)
from app.infrastructure.clients.ollama import OllamaClient, OllamaClientError
from app.infrastructure.clients.planner_service import (
    PlannerServiceAiReadError,
    PlannerServiceClient,
    PlannerServiceClientError,
)


def test_core_service_auth_client_maps_401_from_introspection() -> None:
    """Preserve downstream 401 auth failures from core-service introspection."""

    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"detail": "Access token is invalid."})
    )
    client = CoreServiceAuthClient(
        base_url="http://core-service.test",
        internal_service_token="shared-token",
        transport=transport,
    )

    with pytest.raises(CoreServiceAuthError) as exc_info:
        client.introspect_access_token("bad-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Access token is invalid."


def test_core_service_boundary_client_maps_503_from_internal_helper() -> None:
    """Surface internal core-service helper outages as controlled 503 errors."""

    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, json={"detail": "core helper unavailable"})
    )
    client = CoreServiceAuthClient(
        base_url="http://core-service.test",
        internal_service_token="shared-token",
        transport=transport,
    )

    with pytest.raises(CoreServiceBoundaryError) as exc_info:
        client.get_internal_ai_service_boundary()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "core helper unavailable"


def test_core_service_index_feed_client_rejects_invalid_payload() -> None:
    """Map malformed internal index-feed payloads to controlled 502 errors."""

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"items": []}))
    client = CoreServiceAuthClient(
        base_url="http://core-service.test",
        internal_service_token="shared-token",
        transport=transport,
    )

    with pytest.raises(CoreServiceAiReadError) as exc_info:
        client.list_index_feed(None)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "core-service returned invalid internal AI index feed payload"


def test_planner_service_client_maps_403_from_internal_helper() -> None:
    """Preserve downstream 403 failures from the planner internal AI helper route."""

    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, json={"detail": "Internal service token is invalid."})
    )
    client = PlannerServiceClient(
        base_url="http://planner-service.test",
        internal_service_token="shared-token",
        transport=transport,
    )

    with pytest.raises(PlannerServiceClientError) as exc_info:
        client.get_internal_ai_service_boundary()

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Internal service token is invalid."


def test_planner_service_proposal_context_client_preserves_404() -> None:
    """Preserve planner 404 responses for missing persisted AI context lookups."""

    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, json={"detail": "Plan run was not found."})
    )
    client = PlannerServiceClient(
        base_url="http://planner-service.test",
        internal_service_token="shared-token",
        transport=transport,
    )

    with pytest.raises(PlannerServiceAiReadError) as exc_info:
        client.get_proposal_context(
            plan_run_id="run-1",
            task_id="task-1",
            employee_id="employee-1",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Plan run was not found."


def test_ollama_client_rejects_malformed_embedding_payload() -> None:
    """Reject Ollama embedding responses that do not expose valid embeddings."""

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"embeddings": []}))
    client = OllamaClient(
        base_url="http://ollama.test",
        chat_model="qwen3:4b",
        embed_model="bge-m3",
        transport=transport,
    )

    with pytest.raises(OllamaClientError) as exc_info:
        client.embed_texts(["hello"])

    assert exc_info.value.detail == "ollama embedding payload is invalid"


def test_ollama_client_maps_runtime_unavailability() -> None:
    """Surface transport-level Ollama errors as controlled 503 failures."""

    def _raise_connect_error(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable")

    client = OllamaClient(
        base_url="http://ollama.test",
        chat_model="qwen3:4b",
        embed_model="bge-m3",
        transport=httpx.MockTransport(_raise_connect_error),
    )

    with pytest.raises(OllamaClientError) as exc_info:
        client.generate_explanation(system_prompt="system", user_prompt="user")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "ollama generation runtime is unavailable"


def test_ollama_client_maps_generation_timeout_to_503() -> None:
    """Surface Ollama read timeouts as controlled runtime-unavailable responses."""

    def _raise_timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client = OllamaClient(
        base_url="http://ollama.test",
        chat_model="llama3.2:3b",
        embed_model="bge-m3",
        transport=httpx.MockTransport(_raise_timeout),
    )

    with pytest.raises(OllamaClientError) as exc_info:
        client.generate_explanation(system_prompt="system", user_prompt="user")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "ollama generation runtime is unavailable"


def test_ollama_client_rejects_invalid_generation_payload() -> None:
    """Map malformed non-streaming generation envelopes to controlled 502 errors."""

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"message": {}}))
    client = OllamaClient(
        base_url="http://ollama.test",
        chat_model="qwen3:4b",
        embed_model="bge-m3",
        transport=transport,
    )

    with pytest.raises(OllamaClientError) as exc_info:
        client.generate_explanation(
            system_prompt="system",
            user_prompt="user",
            response_schema={"type": "object"},
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "ollama generation payload is invalid"
