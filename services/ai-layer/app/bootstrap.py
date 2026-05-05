"""Bootstrap helpers for ai-layer runtime foundation."""

import time

from psycopg import Error, OperationalError, connect

from app.config import (
    AI_DB_CONNECT_RETRIES,
    AI_DB_CONNECT_RETRY_DELAY_SECONDS,
    postgres_dsn,
)


def initialize_storage() -> None:
    """Ensure the shared PostgreSQL instance is ready for ai-layer usage."""

    last_error: OperationalError | None = None
    for attempt in range(1, AI_DB_CONNECT_RETRIES + 1):
        try:
            with connect(postgres_dsn(), autocommit=True) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    cursor.execute("CREATE SCHEMA IF NOT EXISTS ai_layer;")
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == AI_DB_CONNECT_RETRIES:
                break
            time.sleep(AI_DB_CONNECT_RETRY_DELAY_SECONDS)
        except Error as exc:
            raise RuntimeError("Failed to initialize ai-layer PostgreSQL foundation.") from exc

    raise RuntimeError(
        "Failed to connect ai-layer to PostgreSQL during startup bootstrap.",
    ) from last_error
