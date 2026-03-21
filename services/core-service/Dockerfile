FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app/services/core-service

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY services/core-service/pyproject.toml services/core-service/poetry.lock* ./
RUN poetry install --only main --no-root

COPY services/core-service/ ./

EXPOSE 8000
