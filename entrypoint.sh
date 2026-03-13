#!/bin/bash
set -e

echo "Starting Metomi Backend Services..."

# 1. Start the Alembic DB migration
echo "Checking and applying database migrations..."
cd /app/backend
alembic upgrade head

# 2. Start the FastAPI server
echo "Starting Uvicorn server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
