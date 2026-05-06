# ai-layer

Bootstrap foundation for the future AI support layer.

Current scope:
- FastAPI runtime with a `/health` endpoint;
- authenticated `GET /api/v1/capabilities` endpoint for frontend auth/capability baseline;
- environment-driven configuration aligned with other backend services;
- PostgreSQL bootstrap that enables `pgvector` and creates the `ai_layer` schema;
- runtime wiring to the local `ollama` container;
- core-service token introspection for `admin|manager` access only.

Current service boundary:
- `core-service` remains business truth;
- `planner-service` remains proposals/diagnostics truth;
- `ai-layer` owns only retrieval index, explanations, and sync metadata.

Current auth and access pattern:
- frontend calls ai-layer with `Authorization: Bearer <access>`;
- ai-layer validates the token through `core-service /api/v1/auth/introspect`;
- ai-layer allows only `admin` and `manager`;
- future internal reads from `core-service` and `planner-service` use `X-Internal-Service-Token`.

Important env vars:
- `AI_LAYER_URL`
- `OLLAMA_BASE_URL`
- `OLLAMA_CHAT_MODEL`
- `OLLAMA_EMBED_MODEL`
- `AI_VECTOR_DIM`
- `AI_TOP_K`
- `AI_SYNC_STALE_SECONDS`
- `INTERNAL_SERVICE_TOKEN`

Planned future scope:
- support explanations for assignment proposals and unassigned diagnostics;
- assistive retrieval over historical planning context stored as derived AI index data;
- optional auxiliary scoring signals that remain advisory only.

Still out of scope in this cycle:
- retrieval/index APIs;
- frontend-facing explanation endpoints;
- any LLM-driven replacement for optimization logic.
