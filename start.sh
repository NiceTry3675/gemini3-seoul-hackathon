#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
DEFAULT_VENV_PY="$ROOT_DIR/.venv/bin/python"
PYTHON_BIN="${PYTHON_BIN:-}"

ensure_python_bin() {
  if [[ -n "$PYTHON_BIN" ]]; then
    if [[ ! -x "$PYTHON_BIN" ]]; then
      echo "Error: PYTHON_BIN is set but not executable: $PYTHON_BIN" >&2
      exit 1
    fi
    return
  fi

  if [[ -x "$DEFAULT_VENV_PY" ]]; then
    PYTHON_BIN="$DEFAULT_VENV_PY"
    return
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found. Install Python 3 or set PYTHON_BIN." >&2
    exit 1
  fi

  echo "Creating backend virtualenv at $ROOT_DIR/.venv ..."
  python3 -m venv "$ROOT_DIR/.venv"
  PYTHON_BIN="$DEFAULT_VENV_PY"
}

ensure_backend_deps() {
  if "$PYTHON_BIN" -c "import uvicorn" >/dev/null 2>&1; then
    return
  fi

  echo "Installing backend dependencies (backend/requirements.txt) ..."
  "$PYTHON_BIN" -m pip install -r "$ROOT_DIR/backend/requirements.txt"

  if ! "$PYTHON_BIN" -c "import uvicorn" >/dev/null 2>&1; then
    echo "Error: uvicorn is still unavailable in $PYTHON_BIN after installation." >&2
    exit 1
  fi
}

if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm not found. Install Node.js/npm first." >&2
  exit 1
fi

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Installing frontend dependencies (frontend/package.json) ..."
  (cd "$ROOT_DIR/frontend" && npm install)
fi

ensure_python_bin
ensure_backend_deps

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  trap - EXIT INT TERM

  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi

  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi

  wait "$BACKEND_PID" >/dev/null 2>&1 || true
  wait "$FRONTEND_PID" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

echo "Starting backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
(
  cd "$ROOT_DIR/backend"
  exec "$PYTHON_BIN" -m uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

echo "Starting frontend on http://${FRONTEND_HOST}:${FRONTEND_PORT}"
(
  cd "$ROOT_DIR/frontend"
  exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

echo "Both services started. Press Ctrl+C to stop."

auto_exit_code=0
set +e
while true; do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    wait "$BACKEND_PID"
    auto_exit_code=$?
    break
  fi

  if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    wait "$FRONTEND_PID"
    auto_exit_code=$?
    break
  fi

  sleep 1
done
set -e

if [[ $auto_exit_code -ne 0 ]]; then
  echo "One service exited with code $auto_exit_code." >&2
fi

exit "$auto_exit_code"
