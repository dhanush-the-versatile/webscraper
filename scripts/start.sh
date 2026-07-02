#!/usr/bin/env bash
# One-command production startup.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found — creating one from .env.example (edit SECRET_KEY for production!)"
  cp .env.example .env
fi

docker compose up -d --build
echo
echo "✔ Talent Discovery Platform is starting."
echo "  App:      http://localhost:${PUBLIC_PORT:-8080}"
echo "  API docs: http://localhost:${PUBLIC_PORT:-8080}/docs"
echo
echo "Follow logs with: docker compose logs -f backend worker"
