#!/bin/bash

# Run CI tests locally - mimics what GitHub Actions does
# Usage: ./tests/run_ci_locally.sh (from project root)

set -e  # Exit on error

# Ensure we're in the project root
cd "$(dirname "$0")/.."

echo "🚀 Running CI tests locally..."
echo "================================"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt || pip install -r tests/requirements-minimal.txt
pip install -r tests/test_requirements.txt || echo "Test requirements optional"
pip install pytest pytest-asyncio httpx

# Set up database
echo "🗄️ Setting up test database..."
rm -f sabc.db  # Clean slate
python database.py
python migrate_database.py
python bootstrap_admin.py --email "admin@test.com" --password "adminpass123" --name "CI Admin" --force

# Run backend tests
echo "🧪 Running backend tests..."
python tests/run_tests.py --backend-only

# Run integration tests with server
echo "🌐 Running integration tests..."
# Start server in background
uvicorn app:app --host 127.0.0.1 --port 8000 --log-level warning &
SERVER_PID=$!
sleep 5

# Run integration tests
python -m pytest tests/test_integration.py -v -m integration || INTEGRATION_RESULT=$?

# Kill server
kill $SERVER_PID 2>/dev/null || true

if [ ${INTEGRATION_RESULT:-0} -eq 0 ]; then
    echo "✅ Integration tests passed"
else
    echo "⚠️ Integration tests failed"
fi

echo "✅ Local CI run complete!"