#!/bin/bash
# Double-click this file in Finder to start the arbitrage scanner.
# It sets up the virtual environment on first run, starts the backend
# and frontend servers, opens the dashboard in your browser, and shuts
# both servers down cleanly when you close this window.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "First-time setup: creating a virtual environment and installing dependencies..."
  python3 -m venv .venv
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
uvicorn backend.main:app --port 8000 &
BACKEND_PID=$!

echo "Starting frontend..."
python3 -m http.server 8001 --directory frontend &
FRONTEND_PID=$!

sleep 2
open "http://localhost:8001"

echo ""
echo "Arbitrage scanner is running."
echo "Dashboard: http://localhost:8001"
echo "Close this window (or press Ctrl+C) to stop both servers."
echo ""

wait
