#!/bin/bash
# Development server script for SABC Tournament Management System

set -e

# Check if database exists, create if not
if [ ! -f sabc.db ]; then
    echo "Database not found. Initializing..."
    python database.py
fi

# Start development server with reload
echo "Starting SABC Tournament Management System (Development Mode)..."
echo "Server will reload automatically when files change."
echo "Access at: http://localhost:8000"

exec uvicorn app:app --reload --host 0.0.0.0 --port 8000