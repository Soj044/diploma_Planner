# ai-layer

Bootstrap foundation for the future AI support layer.

Current scope:
- FastAPI runtime with a `/health` endpoint;
- environment-driven configuration aligned with other backend services;
- PostgreSQL bootstrap that enables `pgvector` and creates the `ai_layer` schema;
- runtime wiring to the local `ollama` container.

Planned future scope:
- support explanations for assignment proposals and unassigned diagnostics;
- assistive retrieval over historical planning context stored as derived AI index data;
- optional auxiliary scoring signals that remain advisory only.

Still out of scope in this cycle:
- retrieval/index APIs;
- frontend-facing explanation endpoints;
- any LLM-driven replacement for optimization logic.
