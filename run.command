#!/bin/bash
# Double-click this file in Finder to start the arbitrage scanner.
# It sets up the virtual environment on first run, starts the backend
# and frontend servers, opens the dashboard in your browser, and shuts
# both servers down cleanly when you close this window.
set -e
cd "$(dirname "$0")"

# The codebase uses `X | None` type syntax (Python 3.10+ only), but macOS
# ships an old python3 (Xcode's bundled 3.9) that some machines have as the
# default `python3` on PATH. Using it silently would create a virtual
# environment that fails deep inside the app with a confusing traceback
# instead of a clear message, so find a real 3.10+ interpreter explicitly.
find_python() {
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
      && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

venv_python_is_new_enough() {
  [ -x ".venv/bin/python3" ] \
    && .venv/bin/python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null
}

if [ -d ".venv" ] && ! venv_python_is_new_enough; then
  echo "Existing .venv uses an old Python version; recreating it with a newer one..."
  rm -rf .venv
fi

if [ ! -d ".venv" ]; then
  PYTHON_BIN="$(find_python)" || {
    echo ""
    echo "This project needs Python 3.10 or newer, and none was found on your Mac."
    echo "Install one from https://www.python.org/downloads/ (or 'brew install python@3.12'),"
    echo "then double-click this file again."
    echo ""
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
  }
  echo "First-time setup: creating a virtual environment with $PYTHON_BIN and installing dependencies..."
  "$PYTHON_BIN" -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

# Free up the ports in case a previous run didn't shut down cleanly.
lsof -ti:8000,8001 | xargs kill -9 2>/dev/null || true

cleanup() {
  echo ""
  echo "Stopping servers..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM HUP

echo "Starting backend..."
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting frontend..."
python3 -m http.server 8001 --directory frontend &
FRONTEND_PID=$!

sleep 2
open "http://localhost:8001" || true

echo ""
echo "Arbitrage scanner is running."
echo "Dashboard: http://localhost:8001"
echo "Close this window (or press Ctrl+C) to stop both servers."
echo ""

wait
