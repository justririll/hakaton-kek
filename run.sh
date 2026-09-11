#!/usr/bin/env bash
# Поднимает бэкенд и фронтенд разом. Ctrl+C останавливает оба.
set -euo pipefail
cd "$(dirname "$0")"

(cd backend && uv sync --quiet && uv run uvicorn app.main:app --port 8000) &
backend=$!
(cd frontend-ml && npm install --silent && npm run dev) &
frontend=$!

trap 'kill $backend $frontend 2>/dev/null || true' INT TERM
echo "бэкенд  → http://127.0.0.1:8000/docs"
echo "интерфейс → http://127.0.0.1:5173"
wait
