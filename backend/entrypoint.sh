#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for DB to be ready - Optional, but good practice
# This requires netcat or pg_isready. For simplicity, we might skip this
# or assume DB is ready if docker-compose `depends_on` is used with healthcheck.
# echo "Waiting for database..."
# For PostgreSQL, you can use pg_isready (requires psql client, might need to be installed in Dockerfile)
# while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do # Assuming these env vars are set
#   sleep 2
# done
# echo "Database started"

# Run database migrations
echo "Running database migrations..."
# Ensure alembic can find its config and the app's config for DB URL
# The working directory is /app, where alembic.ini should be if it's in backend/
python -m alembic upgrade head

# Start the main application (passed as arguments to this script)
# Example: entrypoint.sh uvicorn main:app --host 0.0.0.0 --port 8000
echo "Starting application with command: $@"
exec "$@"
