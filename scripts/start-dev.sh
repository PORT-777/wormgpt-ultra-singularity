#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "============================================================"
echo "  AI Platform - Full Stack Dev Start"
echo "============================================================"

if [ ! -f backend/.env ]; then
  echo "backend/.env missing - copying from .env.example"
  cp backend/.env.example backend/.env
fi

if [ ! -f frontend/.env.local ]; then
  echo "frontend/.env.local missing - creating defaults"
  cat > frontend/.env.local <<'EOF'
VITE_API_BASE=http://127.0.0.1:7777
VITE_WS_BASE=ws://127.0.0.1:7777
VITE_INTERNAL_API_KEY=dev-key-change-me
VITE_APP_NAME=AI Platform
EOF
fi

BACKEND_KEY=$(grep '^INTERNAL_API_KEY=' backend/.env | head -1 | cut -d'=' -f2- | tr -d '[:space:]')
if [ -n "$BACKEND_KEY" ]; then
  if grep -q '^VITE_INTERNAL_API_KEY=' frontend/.env.local; then
    sed -i "s|^VITE_INTERNAL_API_KEY=.*|VITE_INTERNAL_API_KEY=$BACKEND_KEY|" frontend/.env.local
  else
    echo "VITE_INTERNAL_API_KEY=$BACKEND_KEY" >> frontend/.env.local
  fi
  echo "Internal API key synced"
else
  echo "WARNING: INTERNAL_API_KEY not set in backend/.env - internal routes will be disabled"
fi

echo "Starting backend on :7777..."
(cd backend && python -m uvicorn backend.main:app --host 127.0.0.1 --port 7777) &
BACKEND_PID=$!

echo "Waiting for backend..."
for i in $(seq 1 45); do
  if curl -fsS http://127.0.0.1:7777/health >/dev/null 2>&1; then
    echo "Backend ready"
    break
  fi
  sleep 1
  if [ "$i" -eq 45 ]; then
    echo "Backend failed to start in 45s"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
  fi
done

echo "Starting frontend on :5173..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!
sleep 3

echo "============================================================"
echo "Frontend:  http://127.0.0.1:5173/"
echo "Console:   http://127.0.0.1:5173/platform.html"
echo "API docs:  http://127.0.0.1:7777/api/docs"
echo "OpenAPI:   http://127.0.0.1:7777/api/openapi.json"
echo "============================================================"

sleep 2
echo "Running live integration smoke tests..."
(cd frontend && VITE_TEST_LIVE=true npm test -- src/test/integration/live.test.ts) || true

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; echo Stopped.' INT TERM
wait
