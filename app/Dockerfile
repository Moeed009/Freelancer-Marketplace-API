# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app


ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1


COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev


COPY . .
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"


RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
