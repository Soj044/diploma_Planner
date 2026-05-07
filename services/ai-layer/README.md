# ai-layer

Bootstrap foundation for the future AI support layer.

Current scope:
- FastAPI runtime with a `/health` endpoint;
- authenticated `GET /api/v1/capabilities` endpoint for frontend auth/capability baseline;
- authenticated `POST /api/v1/explanations/assignment-rationale` endpoint for advisory proposal explanations;
- authenticated `POST /api/v1/explanations/unassigned-task` endpoint for advisory unassigned-task explanations;
- environment-driven configuration aligned with other backend services;
- PostgreSQL repository/bootstrap that enables `pgvector`, creates the `ai_layer` schema, and maintains:
  - `ai_layer.index_items`
  - `ai_layer.sync_state`
  - `ai_layer.explanation_logs`;
- runtime wiring to the local `ollama` container;
- core-service token introspection for `admin|manager` access only;
- internal full/incremental sync over:
  - `assignment_case` feed from `core-service`
  - `unassigned_case` feed from `planner-service`;
- live context reads for:
  - task + employee assignment explanation context from `core-service`
  - persisted proposal/unassigned context from `planner-service`;
- structured explanation generation through `Ollama /api/chat` with JSON-schema output;
- CLI full reindex entrypoint: `poetry run python -m app.cli.reindex --mode full`.

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

Current retrieval/index scope:
- `assignment_case` uses current flattened successful-assignment state from `core-service`;
- `unassigned_case` uses completed persisted diagnostics from `planner-service`;
- `employee/schedule/leave` stay out of the vector corpus and are used only as live context.

Still out of scope in this cycle:
- frontend UI wiring for AI explanations;
- richer hybrid retrieval or document-based RAG;
- any LLM-driven replacement for optimization logic.
