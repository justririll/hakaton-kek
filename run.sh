#!/usr/bin/env bash
# Поднимает бэкенд и фронтенд разом. Ctrl+C останавливает оба.
set -euo pipefail
cd "$(dirname "$0")"

for command in uv npm setsid; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Не найдена команда: $command. Установите её и повторите запуск." >&2
    exit 1
  fi
done

backend_pid=''
frontend_pid=''
cleanup() {
  # Отдельные группы включают дочерние процессы uv/npm и сами серверы.
  for pid in "$backend_pid" "$frontend_pid"; do
    if [[ -n "$pid" ]]; then
      kill -- "-$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Устанавливаем до запуска серверов: ошибка должна остановить весь запуск,
# а не оставлять работающий бэкенд без интерфейса. Отслеживаем и установщики,
# чтобы прерывание не оставляло uv/npm с блокировкой окружения.
echo "[1/3] Проверяю зависимости бэкенда…"
(cd backend && exec setsid uv sync --locked) &
backend_pid=$!
wait "$backend_pid"
backend_pid=''
echo "[2/3] Устанавливаю зависимости фронтенда из package-lock.json…"
# ci восстанавливает и неполный node_modules после прерванной установки.
(cd frontend-ml && exec setsid npm ci --prefer-offline --no-audit --no-fund --fetch-retries=1 --fetch-timeout=30000) &
frontend_pid=$!
wait "$frontend_pid"
frontend_pid=''

echo "[3/3] Запускаю серверы. Дождитесь сообщения Vite «Local» и готовности API."
(cd backend && exec setsid uv run --no-sync uvicorn app.main:app --host 127.0.0.1 --port 8000) &
backend_pid=$!
(cd frontend-ml && exec setsid npm run dev) &
frontend_pid=$!

status=0
wait -n "$backend_pid" "$frontend_pid" || status=$?
echo "Один из серверов остановился (код $status). Причина указана выше; останавливаю второй." >&2
if [[ "$status" -eq 0 ]]; then status=1; fi
exit "$status"
