"""Environment-backed ai-layer configuration."""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")

CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://localhost:8000")
PLANNER_SERVICE_URL = os.getenv("PLANNER_SERVICE_URL", "http://localhost:8001")
AI_LAYER_URL = os.getenv("AI_LAYER_URL", "http://localhost:8002")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:4b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")

AI_VECTOR_DIM = int(os.getenv("AI_VECTOR_DIM", "1024"))
AI_TOP_K = int(os.getenv("AI_TOP_K", "5"))
AI_SYNC_STALE_SECONDS = int(os.getenv("AI_SYNC_STALE_SECONDS", "300"))
AI_DB_CONNECT_RETRIES = int(os.getenv("AI_DB_CONNECT_RETRIES", "10"))
AI_DB_CONNECT_RETRY_DELAY_SECONDS = float(
    os.getenv("AI_DB_CONNECT_RETRY_DELAY_SECONDS", "1"),
)

POSTGRES_DB = os.getenv("POSTGRES_DB", "workestrator")
POSTGRES_USER = os.getenv("POSTGRES_USER", "workestrator")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "workestrator")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))


def postgres_dsn() -> str:
    """Build a psycopg-compatible DSN for ai-layer storage bootstrap."""

    user = quote_plus(POSTGRES_USER)
    password = quote_plus(POSTGRES_PASSWORD)
    return f"postgresql://{user}:{password}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
