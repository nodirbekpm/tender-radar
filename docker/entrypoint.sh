#!/usr/bin/env bash
set -e

echo "[entrypoint] Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT} ..."
python docker/wait_for_db.py

# Only the web container runs migrations/static (RUN_MIGRATIONS=1); workers skip it.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "[entrypoint] Applying migrations ..."
  python manage.py migrate --noinput
  echo "[entrypoint] Collecting static ..."
  python manage.py collectstatic --noinput || true
fi

exec "$@"
