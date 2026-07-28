# SmartGrad

- `main.py` — FastAPI routes (upload form + result page)
- `parser.py` — extracts course code/credit/grade rows out of the transcript PDF with `pdfplumber`
- `dashboard.py` — matches parsed courses against `curriculum.json` and computes progress
- `templates/index.html` — the single upload/results page (Jinja2)

## Prerequisites

- Python 3.12
- Docker (optional)

## Option A: Run locally with plain pip

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install fastapi[standard] jinja2 pdfplumber
fastapi dev main.py
```

This starts the dev server with auto-reload at http://localhost:8000.

To run it production-style instead:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Option A2: Run locally with uv

If you already use [uv](https://docs.astral.sh/uv/), it'll install the exact pinned versions from `uv.lock`:

```bash
uv sync
uv run fastapi dev main.py
```

## Option B: Run with Docker

No local Python setup needed at all:

```bash
docker compose up --build
```

The app is served at http://localhost:8000 (mapped to container port 8080). The compose file mounts your source into the container for live-reload, so code edits pick up without rebuilding.

To run the production image directly, without compose:

```bash
docker build -t smartgrad .
docker run -p 8080:8080 smartgrad
```

## Deployment

The `Dockerfile` reads the `PORT` env var (defaulting to 8080), which matches what Google Cloud Run expects — build and deploy the image there via `gcloud run deploy`.
