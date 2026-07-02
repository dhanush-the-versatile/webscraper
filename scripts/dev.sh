#!/usr/bin/env bash
# Local development: infra in Docker, app processes with hot reload.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up -d db redis

echo "Starting backend (http://localhost:8000) and frontend (http://localhost:3000)..."
(
  cd backend
  [ -d .venv ] || python3 -m venv .venv
  . .venv/bin/activate
  pip install -q -r requirements-dev.txt
  export DATABASE_URL="postgresql+asyncpg://talent:talent@localhost:5432/talent"
  alembic upgrade head
  uvicorn app.main:app --reload --port 8000 &
)
(
  cd frontend
  [ -d node_modules ] || npm install --no-audit --no-fund
  npm run dev &
)
wait
