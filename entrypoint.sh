#!/usr/bin/env bash
set -euo pipefail

# Apply DB migrations, then start the server.
echo "Running migrations..."
alembic upgrade head

WORKERS="${WEB_CONCURRENCY:-2}"
echo "Starting gunicorn with ${WORKERS} uvicorn workers..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WORKERS}" \
    --bind 0.0.0.0:8000 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
