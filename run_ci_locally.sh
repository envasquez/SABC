#!/bin/bash

# Run CI tests locally - mimics what GitHub Actions does
# Usage: ./run_ci_locally.sh

set -e  # Exit on error

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
python bootstrap_admin.py --email "admin@test.com" --password "adminpass123" --name "CI Admin" --force

# Run backend tests
echo "🧪 Running backend tests..."
python tests/run_tests.py --backend-only

echo "✅ Local CI run complete!"