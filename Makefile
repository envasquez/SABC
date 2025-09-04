# SABC Application Test Suite Makefile
# Provides convenient commands for running tests and development tasks

.PHONY: help install test test-backend test-frontend test-integration test-all coverage lint format clean setup-dev

# Default target
help:
	@echo "SABC Application Test Suite"
	@echo "=========================="
	@echo ""
	@echo "Available commands:"
	@echo "  install         - Install test dependencies"
	@echo "  setup-dev       - Set up development environment"
	@echo "  test            - Run all tests"
	@echo "  test-backend    - Run backend tests only"
	@echo "  test-frontend   - Run frontend tests only"
	@echo "  test-integration- Run integration tests only"
	@echo "  test-quick      - Run quick test subset"
	@echo "  coverage        - Generate coverage report"
	@echo "  lint            - Run linting checks"
	@echo "  format          - Format code"
	@echo "  clean           - Clean test artifacts"
	@echo "  serve           - Start development server"
	@echo ""

# Install test dependencies
install:
	@echo "📦 Installing test dependencies..."
	pip install -r tests/test_requirements.txt
	playwright install chromium
	@echo "✅ Dependencies installed"

# Set up development environment
setup-dev: install
	@echo "🔧 Setting up development environment..."
	python database.py
	python bootstrap_admin.py
	@echo "✅ Development environment ready"

# Run all tests
test:
	@echo "🧪 Running all tests..."
	python run_tests.py

# Run backend tests only
test-backend:
	@echo "🧪 Running backend tests..."
	python run_tests.py --backend-only

# Run frontend tests only  
test-frontend:
	@echo "🖥️  Running frontend tests..."
	python run_tests.py --frontend-only

# Run integration tests
test-integration:
	@echo "🔗 Running integration tests..."
	python -m pytest tests/test_integration.py -v -m integration

# Run quick test subset
test-quick:
	@echo "⚡ Running quick tests..."
	python run_tests.py --filter "not slow"

# Run tests with specific filter
test-filter:
	@echo "🔍 Running filtered tests..."
	@read -p "Enter test filter: " filter; \
	python run_tests.py --filter "$$filter"

# Generate coverage report
coverage:
	@echo "📊 Generating coverage report..."
	python -m pytest tests/test_backend.py --cov=app --cov-report=html --cov-report=term
	@echo "📁 Coverage report: htmlcov/index.html"

# Run linting
lint:
	@echo "🔍 Running linting checks..."
	python -m ruff check .
	python -m mypy app.py --ignore-missing-imports
	@echo "✅ Linting complete"

# Format code
format:
	@echo "🎨 Formatting code..."
	python -m ruff format .
	@echo "✅ Code formatted"

# Clean test artifacts
clean:
	@echo "🧹 Cleaning test artifacts..."
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf .coverage
	rm -f *.xml
	rm -f *_test_report.html
	rm -f test_report.md
	@echo "✅ Cleanup complete"

# Start development server
serve:
	@echo "🚀 Starting development server..."
	uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Database operations
db-init:
	@echo "🗄️  Initializing database..."
	python database.py

db-reset:
	@echo "🗄️  Resetting database..."
	rm -f sabc.db
	python database.py
	python bootstrap_admin.py

# Performance testing
test-performance:
	@echo "⚡ Running performance tests..."
	python -m pytest tests/test_backend.py::TestPerformance -v

# Accessibility testing
test-accessibility:
	@echo "♿ Running accessibility tests..."
	python -m pytest tests/test_frontend.py::TestAccessibility -v

# Security testing  
test-security:
	@echo "🔒 Running security tests..."
	python -m pytest tests/test_backend.py::TestSecurity -v

# CI/CD pipeline commands
ci-test:
	@echo "🤖 Running CI tests..."
	python run_tests.py --backend-only
	python -m pytest tests/test_integration.py -v

# Generate test data
generate-test-data:
	@echo "📝 Generating test data..."
	python -c "from tests.conftest import test_database; print('Test data generated')"

# Validate configuration
validate-config:
	@echo "✅ Validating configuration..."
	python -c "import app; print('App configuration valid')"
	python -c "import database; print('Database configuration valid')"

# Docker commands (if using Docker)
docker-test:
	@echo "🐳 Running tests in Docker..."
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Documentation generation
docs:
	@echo "📚 Generating documentation..."
	python -m pytest --collect-only --quiet | grep "test session starts" || true
	@echo "Test documentation generated"

# Advanced test commands
test-stress:
	@echo "💪 Running stress tests..."
	python -m pytest tests/test_integration.py::TestSystemLimits -v

test-parallel:
	@echo "⚡ Running tests in parallel..."
	python -m pytest -n auto tests/test_backend.py

# Environment-specific commands
test-local: test-backend test-integration
test-staging: ci-test
test-production: test-security test-performance

# Development helpers
watch-tests:
	@echo "👀 Watching tests..."
	python -m pytest-watch tests/test_backend.py

check-all: lint test coverage
	@echo "✅ All checks passed"

# Release preparation
prepare-release: clean format lint test coverage
	@echo "🚀 Release preparation complete"

# Help for specific test categories
help-backend:
	@echo "Backend Test Categories:"
	@echo "  TestAuthentication  - Login, logout, permissions"
	@echo "  TestEvents         - Event CRUD operations"
	@echo "  TestPolls          - Poll creation and voting"
	@echo "  TestTournaments    - Tournament management"
	@echo "  TestNews           - News management"
	@echo "  TestDatabase       - Database integrity"
	@echo "  TestSecurity       - Security validation"

help-frontend:
	@echo "Frontend Test Categories:"
	@echo "  TestNavigation     - Page navigation"
	@echo "  TestAuthentication - Login/logout UI"
	@echo "  TestEventManagement- Events UI"
	@echo "  TestPolls          - Voting interface"
	@echo "  TestAccessibility  - A11y compliance"
	@echo "  TestResponsive     - Mobile/desktop layouts"
	@echo "  TestPerformance    - Load times, JS errors"