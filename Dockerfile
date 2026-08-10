FROM python:3.12-slim-bookworm

# Copy 'uv' package manager from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
RUN useradd --create-home --uid 1000 app

# Copy pyproject.toml
COPY pyproject.toml ./

# Install dependencies directly from pyproject.toml using uv
# This is much faster than pip and doesn't require a requirements.txt file
RUN uv pip install --system -r pyproject.toml

# Copy the rest of the application source code
COPY --chown=app:app main.py parser.py dashboard.py database.py models.py seed.py config.py services.py init.sql ./
COPY --chown=app:app routers/ ./routers/
COPY --chown=app:app templates/ ./templates/

RUN chown -R app:app /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

USER app
EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
