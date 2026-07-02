#!/bin/sh
# Wait for the database, apply migrations (API container only), then exec.
set -e

host="${POSTGRES_SERVER:-db}"
port="${POSTGRES_PORT:-5432}"

echo "Waiting for PostgreSQL at ${host}:${port}..."
retries=60
until python - <<PYEOF
import socket, sys
try:
    socket.create_connection(("${host}", int("${port}")), timeout=2).close()
except OSError:
    sys.exit(1)
PYEOF
do
  retries=$((retries - 1))
  if [ "$retries" -le 0 ]; then
    echo "PostgreSQL did not become available in time" >&2
    exit 1
  fi
  sleep 1
done
echo "PostgreSQL is up."

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
fi

exec "$@"
