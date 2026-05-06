"""Entrypoint for the ai-layer application.

This module assembles the FastAPI service, runs the shared PostgreSQL bootstrap,
and registers the public capability plus explanation routes that will back the
future AI-assisted retrieval and explanation flow.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.capabilities import router as capabilities_router
from app.api.explanations import router as explanations_router
from app.bootstrap import initialize_storage


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize AI storage prerequisites before the API starts serving traffic."""

    initialize_storage()
    yield


def create_application() -> FastAPI:
    """Build the ai-layer FastAPI application with all public routers attached."""

    application = FastAPI(title="ai-layer", version="0.1.0", lifespan=lifespan)
    application.include_router(capabilities_router)
    application.include_router(explanations_router)
    return application


app = create_application()


@app.get("/health")
def health() -> dict[str, str]:
    """Expose a minimal health probe for compose/runtime checks."""

    return {"status": "ok"}
