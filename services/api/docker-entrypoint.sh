#!/bin/sh
# Purpose: Copies the seed catalog only when needed, applies API migrations and starts the supplied server/worker command.
set -eu
# Copy the preserved seed once into a separately persisted, writable catalog.
if [ -n "${CATALOG_SEED_PATH:-}" ] && [ ! -f "${TRAVEL_DATABASE_DIR}/travel_data_complete.db" ]; then
    cp "$CATALOG_SEED_PATH" "${TRAVEL_DATABASE_DIR}/travel_data_complete.db"
fi
if [ "${1:-}" = "gunicorn" ]; then
    alembic upgrade head
fi
exec "$@"
