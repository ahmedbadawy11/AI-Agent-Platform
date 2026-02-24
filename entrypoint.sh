#!/bin/bash
set -e

DB_URL="postgresql://${POSTGRES_USERNAME}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_MAIN_DATABASE}"

# Create database if it doesn't exist
echo "Ensuring database '${POSTGRES_MAIN_DATABASE}' exists ..."
PGPASSWORD="$POSTGRES_PASSWORD" createdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USERNAME" "$POSTGRES_MAIN_DATABASE" 2>/dev/null || true

# Run Alembic migrations
echo "Running migrations ..."
cd models/ai_agent_platform_DB
cp alembic.ini.example alembic.ini
sed -i "s|sqlalchemy.url = driver://user:pass@localhost/dbname|sqlalchemy.url = ${DB_URL}|" alembic.ini
alembic upgrade head
cd /app

# Start the application
echo "Starting application ..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
