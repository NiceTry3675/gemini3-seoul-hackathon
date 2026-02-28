#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_READY_TIMEOUT_SECONDS="${BACKEND_READY_TIMEOUT_SECONDS:-30}"
if [[ -n "${BACKEND_APP_MODULE:-}" ]]; then
  BACKEND_APP_MODULES="$BACKEND_APP_MODULE"
else
  BACKEND_APP_MODULES="${BACKEND_APP_MODULES:-app.main}"
fi
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

kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "Killing existing processes on port $port (PIDs: $(echo $pids | tr '\n' ' '))..."
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 1
    # Force kill any remaining
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
  fi
}

ensure_python_bin
ensure_backend_deps

kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

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

wait_for_backend() {
  local endpoint="http://${BACKEND_HOST}:${BACKEND_PORT}"
  local elapsed=0
  local paths=("/api/health" "/healthz" "/")

  while (( elapsed < BACKEND_READY_TIMEOUT_SECONDS )); do
    if command -v curl >/dev/null 2>&1; then
      for path in "${paths[@]}"; do
        if curl -sSf "${endpoint}${path}" >/dev/null 2>&1; then
          return 0
        fi
      done
    else
      if command -v nc >/dev/null 2>&1; then
        if nc -z "$BACKEND_HOST" "$BACKEND_PORT" >/dev/null 2>&1; then
          return 0
        fi
      fi
    fi

    sleep 1
    elapsed=$((elapsed + 1))
  done

  return 1
}

normalize_backend_module() {
  local module="$1"
  if [[ "$module" == backend.* ]]; then
    module="${module#backend.}"
  fi
  echo "$module"
}

verify_backend_module() {
  local module="$1"
  local normalized
  normalized="$(normalize_backend_module "$module")"
  local -r check_cmd="import importlib.util; import sys; sys.path.insert(0, '$ROOT_DIR/backend'); raise SystemExit(0 if importlib.util.find_spec('$normalized') else 1)"

  if env "PYTHONPATH=$ROOT_DIR/backend:${PYTHONPATH:+$PYTHONPATH}" \
    "$PYTHON_BIN" -c "$check_cmd" >/dev/null 2>&1; then
    echo "$normalized"
    return 0
  fi

  return 1
}

run_uvicorn() {
  local module="$1"
  cd "$ROOT_DIR/backend"
  exec env "PYTHONPATH=$ROOT_DIR/backend:${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON_BIN" -m uvicorn "${module}:app" --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
}

start_backend() {
  IFS="," read -r -a modules <<< "$BACKEND_APP_MODULES"

  for candidate in "${modules[@]}"; do
    local normalized
    normalized="$(verify_backend_module "$candidate" || true)"
    if [[ -n "$normalized" ]]; then
      echo "Starting backend with module: $normalized"
      run_uvicorn "$normalized"
      return 0
    fi
  done

  echo "Error: No valid backend module found. Checked: $BACKEND_APP_MODULES" >&2
  return 1
}

trap cleanup EXIT INT TERM

echo "Starting backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
(
  start_backend
) &
BACKEND_PID=$!

echo "Waiting for backend to become ready..."
if ! wait_for_backend; then
  echo "Error: backend did not become ready on http://${BACKEND_HOST}:${BACKEND_PORT} within ${BACKEND_READY_TIMEOUT_SECONDS}s." >&2
  exit 1
fi

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
