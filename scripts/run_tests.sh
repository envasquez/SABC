#!/bin/bash
# Run the SABC test suite

set -e

echo "🧪 Running SABC Test Suite"
echo "=========================="
echo ""

# Check if DATABASE_URL is set for test database
export DATABASE_URL="postgresql://postgres:dev123@localhost:5432/sabc_test"

# Check if test database exists, create if not
echo "📦 Checking test database..."
psql -h localhost -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'sabc_test'" | grep -q 1 || \
    psql -h localhost -U postgres -c "CREATE DATABASE sabc_test"

echo "✅ Test database ready"
echo ""

# Run pytest with coverage if requested
if [ "$1" == "--coverage" ]; then
    echo "📊 Running tests with coverage..."
    pytest tests/ --cov=core --cov=routes --cov-report=html --cov-report=term
else
    echo "🧪 Running tests..."
    pytest tests/ "$@"
fi

echo ""
echo "✅ Tests complete!"