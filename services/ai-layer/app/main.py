"""Entrypoint for the ai-layer bootstrap service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap import initialize_storage


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize AI storage prerequisites before the API starts."""

    initialize_storage()
    yield


app = FastAPI(title="ai-layer", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Expose a minimal health probe for compose/runtime checks."""

    return {"status": "ok"}
