"""HTTP client for the local Ollama runtime.

This module exposes the minimum embedding and generation interfaces that the
current ai-layer cycle needs while keeping error handling stable for the next
retrieval and prompt-building iteration. It supports batch embeddings and
non-streaming structured chat output through Ollama's native `/api/chat`.
"""

from collections.abc import Sequence

import httpx


class OllamaClientError(Exception):
    """Raised when the local Ollama runtime is unavailable or returns bad data."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class OllamaClient:
    """Call the local Ollama runtime for embeddings and future explanations."""

    def __init__(
        self,
        *,
        base_url: str,
        chat_model: str,
        embed_model: str,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Configure the Ollama client with chat and embedding model names."""

        self._base_url = base_url.rstrip("/")
        self._chat_model = chat_model
        self._embed_model = embed_model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed one or more texts through Ollama's embedding endpoint."""

        if not texts:
            return []

        payload = self._request_json(
            path="/api/embed",
            body={"model": self._embed_model, "input": texts},
            unavailable_detail="ollama embedding runtime is unavailable",
        )
        embeddings = payload.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            return [self._coerce_embedding(vector) for vector in embeddings]

        single_embedding = payload.get("embedding")
        if isinstance(single_embedding, list):
            return [self._coerce_embedding(single_embedding)]

        raise OllamaClientError(status_code=502, detail="ollama embedding payload is invalid")

    def generate_explanation(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, object] | str | None = None,
        temperature: float = 0.1,
    ) -> str:
        """Generate one non-streaming explanation response through Ollama chat."""

        body: dict[str, object] = {
            "model": self._chat_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": temperature},
        }
        if response_schema is not None:
            body["format"] = response_schema

        payload = self._request_json(
            path="/api/chat",
            body=body,
            unavailable_detail="ollama generation runtime is unavailable",
        )
        message = payload.get("message")
        if not isinstance(message, dict):
            raise OllamaClientError(status_code=502, detail="ollama generation payload is invalid")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaClientError(status_code=502, detail="ollama generation payload is invalid")
        return content

    def _request_json(
        self,
        *,
        path: str,
        body: dict[str, object],
        unavailable_detail: str,
    ) -> dict[str, object]:
        """Execute one JSON POST request against the local Ollama runtime."""

        try:
            with httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(path, json=body)
        except httpx.HTTPError as exc:
            raise OllamaClientError(status_code=503, detail=unavailable_detail) from exc

        if response.status_code >= 400:
            raise OllamaClientError(status_code=503, detail=unavailable_detail)

        try:
            payload = response.json()
        except ValueError as exc:
            raise OllamaClientError(status_code=502, detail=f"{path} returned invalid JSON payload") from exc
        if not isinstance(payload, dict):
            raise OllamaClientError(status_code=502, detail=f"{path} returned invalid JSON payload")
        return payload

    def _coerce_embedding(self, raw_embedding: Sequence[object]) -> list[float]:
        """Validate and convert one Ollama embedding vector to floats."""

        try:
            return [float(value) for value in raw_embedding]
        except (TypeError, ValueError) as exc:
            raise OllamaClientError(status_code=502, detail="ollama embedding payload is invalid") from exc
