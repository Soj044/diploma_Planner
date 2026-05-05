FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app/services/ai-layer

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY services/ai-layer/pyproject.toml services/ai-layer/poetry.lock* ./
RUN poetry install --only main --no-root

COPY services/ai-layer/ ./

EXPOSE 8002
