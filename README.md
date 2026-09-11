# FastAPI starter

A small Python API managed with [uv](https://docs.astral.sh/uv/), with a health
endpoint, automatic API documentation, pytest, and Ruff.

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```bash
uv sync --locked
uv run fastapi dev
```

The project pins Python 3.14 for development and supports Python 3.12 or newer.
uv automatically downloads the pinned interpreter if needed and creates `.venv`.
You do not need to activate the environment when using `uv run`.

- API: http://127.0.0.1:8000/
- Health: http://127.0.0.1:8000/health
- Analytics dashboard: http://127.0.0.1:8000/api/v1/analytics/dashboard
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Project structure

```text
app/
  main.py             # Application and router registration
  routers/health.py   # Health endpoint and response schema
tests/test_api.py     # API smoke test
pyproject.toml        # Dependencies and tool configuration
uv.lock              # Reproducible dependency versions
```

Add route modules under `app/routers/` and register them with
`app.include_router(...)` in `app/main.py`.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Format code with `uv run ruff format .`.

```bash
uv add package-name
uv add --dev package-name
```

Commit both `pyproject.toml` and `uv.lock` when changing dependencies.

## Run without auto-reload

```bash
uv sync --locked --no-dev
uv run --no-dev fastapi run --host 0.0.0.0 --port 8000
```

The health endpoint reports that the application is running; add dependency
checks if the application later requires a database or other services.

## Frontend

The Vue 3 dashboard is in `frontend/`. Run the API first, then start the Vite
development server:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. During development, Vite proxies `/api` requests to
FastAPI at `http://127.0.0.1:8000`.

See the [FastAPI CLI documentation](https://fastapi.tiangolo.com/fastapi-cli/)
and [uv project guide](https://docs.astral.sh/uv/guides/projects/) for more details.
