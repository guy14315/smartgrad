FROM python:3.12-slim-bookworm

WORKDIR /app
RUN useradd --create-home --uid 1000 app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY --chown=app:app app/ ./app/

RUN chown -R app:app /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

USER app
EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
