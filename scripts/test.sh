#!/usr/bin/env bash
# Run the full test suite (backend + frontend).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "── Backend tests ──"
(cd backend && . .venv/bin/activate 2>/dev/null || true && python -m pytest -q)

echo "── Frontend tests ──"
(cd frontend && npx vitest run)
