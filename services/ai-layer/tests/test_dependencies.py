"""Unit tests for ai-layer dependency providers.

This module verifies that dependency wiring keeps the shared Ollama client
aligned with environment-backed runtime defaults such as timeout and model
selection.
"""

import importlib

from app import config, dependencies


def test_get_ollama_client_uses_timeout_and_default_models(monkeypatch) -> None:
    """Wire the shared Ollama dependency from config-backed timeout and model defaults."""

    monkeypatch.setattr(config, "OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setattr(config, "OLLAMA_CHAT_MODEL", "llama3.2:3b")
    monkeypatch.setattr(config, "OLLAMA_EMBED_MODEL", "bge-m3")
    monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 90.0)
    importlib.reload(dependencies)
    dependencies.get_ollama_client.cache_clear()

    try:
        client = dependencies.get_ollama_client()
        assert client._base_url == "http://ollama.test"
        assert client._chat_model == "llama3.2:3b"
        assert client._embed_model == "bge-m3"
        assert client._timeout_seconds == 90.0
    finally:
        importlib.reload(config)
        importlib.reload(dependencies)
        dependencies.get_ollama_client.cache_clear()
