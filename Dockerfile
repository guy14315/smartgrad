# --- build stage ---
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies if needed (none strictly needed for these packages, but standard practice)
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# --- runtime stage ---
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN useradd --create-home --uid 1000 app

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

COPY --chown=app:app main.py parser.py dashboard.py database.py models.py seed.py init.sql ./
COPY --chown=app:app routers/ ./routers/
COPY --chown=app:app templates/ ./templates/

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

USER app
EXPOSE 8080

# Cloud Run injects $PORT; the default above covers local runs.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
