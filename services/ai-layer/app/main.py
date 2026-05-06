"""Entrypoint for the ai-layer application.

This file assembles the FastAPI app, bootstraps shared PostgreSQL prerequisites,
and wires public health plus authenticated ai-layer capability routes.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.capabilities import router as capabilities_router
from app.bootstrap import initialize_storage


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize AI storage prerequisites before the API starts."""

    initialize_storage()
    yield


app = FastAPI(title="ai-layer", version="0.1.0", lifespan=lifespan)
app.include_router(capabilities_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Expose a minimal health probe for compose/runtime checks."""

    return {"status": "ok"}
