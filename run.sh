#!/usr/bin/env bash
# Поднимает бэкенд и фронтенд разом. Ctrl+C останавливает оба.
set -euo pipefail
cd "$(dirname "$0")"

# Ключ Gemini лежит в .env (см. .env.example) и в репозиторий не попадает.
# Без него платформа работает, но вместо AI-резюме отдаётся детерминированный текст.
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

(cd backend && uv sync --quiet && uv run uvicorn app.main:app --port 8010) &
backend=$!
(cd frontend-ml && npm install --silent && npm run dev) &
frontend=$!

trap 'kill $backend $frontend 2>/dev/null || true' INT TERM
echo "бэкенд  → http://127.0.0.1:8010/docs"
echo "интерфейс → http://127.0.0.1:5180"
wait
