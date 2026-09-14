# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-install-project --no-dev

COPY . .

RUN uv sync --locked --no-dev

RUN useradd --create-home appuser && chown -R appuser:appuser /app

USER appuser

CMD ["sh", "-c", "alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]