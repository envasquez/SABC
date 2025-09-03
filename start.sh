#!/bin/bash
# Start script for SABC Tournament Management System

set -e

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if database exists, create if not
if [ ! -f sabc.db ]; then
    echo "Database not found. Initializing..."
    python database.py
fi

# Start with gunicorn in production mode
echo "Starting SABC Tournament Management System..."
echo "Environment: ${ENVIRONMENT:-production}"
echo "Host: ${HOST:-0.0.0.0}:${PORT:-8000}"
echo "Workers: ${WORKERS:-4}"

exec gunicorn app:app -c gunicorn.conf.py