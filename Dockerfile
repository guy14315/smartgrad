# --- build stage: resolve dependencies into a venv ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Copied separately so the dependency layer is cached across code changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev


# --- runtime stage ---
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN useradd --create-home --uid 1000 app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app main.py parser.py dashboard.py curriculum.json ./
COPY --chown=app:app templates/ ./templates/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080

USER app
EXPOSE 8080

# Cloud Run injects $PORT; the default above covers local runs.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
