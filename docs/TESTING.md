# Testing Guide - SABC Tournament Management

## Overview

This document describes the comprehensive test suite for the SABC Tournament Management System. The test suite ensures production readiness, code quality, and security.

---

## Quick Start

### Install Test Dependencies

```bash
# Using pip
pip install -r requirements-test.txt

# Or in Nix development environment
nix develop
```

### Run Tests

```bash
# Run all tests (in Nix environment)
nix develop -c run-tests

# Run specific test categories
pytest tests/unit/ -v
pytest tests/routes/ -v
pytest tests/security/ -v

# Run with coverage report
nix develop -c run-tests --coverage

# Run in parallel (faster)
pytest -n auto
```

---

## Test Suite Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_auth_helpers.py
│   ├── test_password_validator.py
│   ├── test_tournament_points.py
│   └── test_query_service.py
├── integration/             # Integration tests (database, services)
│   ├── test_database_operations.py
│   ├── test_email_service.py
│   └── test_session_management.py
├── routes/                  # Route/endpoint tests
│   ├── test_auth_routes.py
│   ├── test_voting_routes.py
│   ├── test_admin_routes.py
│   └── test_tournament_routes.py
└── security/                # Security tests
    ├── test_csrf_protection.py
    ├── test_sql_injection.py
    ├── test_xss_prevention.py
    └── test_authorization.py
```

---

## Test Categories

### Unit Tests
**Fast, isolated tests for individual functions and classes**

- No database access
- No external services
- Pure function testing
- Mock all dependencies

**Examples:**
- Password validation logic
- Tournament points calculation
- Date/time formatting
- Helper functions

**Run:**
```bash
pytest tests/unit/ -v
```

### Integration Tests
**Tests for database operations and service interactions**

- Uses test database (in-memory SQLite)
- Tests database models and queries
- Tests service layer integration
- Tests email sending (mocked)

**Examples:**
- Creating/updating database records
- Complex database queries
- Session management
- Transaction rollback scenarios

**Run:**
```bash
pytest tests/integration/ -v
```

### Route Tests
**Tests for FastAPI endpoints and HTTP behavior**

- Uses FastAPI TestClient
- Tests request/response cycles
- Tests authentication/authorization
- Tests form submissions

**Examples:**
- Login/logout functionality
- Member registration
- Poll voting
- Tournament result submission
- Admin actions

**Run:**
```bash
pytest tests/routes/ -v
```

### Security Tests
**Tests for security vulnerabilities**

- CSRF token validation
- SQL injection attempts
- XSS (Cross-site scripting) prevention
- Authorization bypass attempts
- Rate limiting
- Session security

**Examples:**
- Submitting forms without CSRF tokens
- Injecting SQL in form fields
- Attempting to access admin routes as regular user
- Session fixation attacks

**Run:**
```bash
pytest tests/security/ -v
```

---

## Test Fixtures

### Database Fixtures

```python
# Fresh database for each test
def test_something(db_session):
    user = Angler(name="Test")
    db_session.add(user)
    db_session.commit()
```

### User Fixtures

```python
# Pre-created users with different roles
def test_member_access(member_user):
    assert member_user.member is True

def test_admin_access(admin_user):
    assert admin_user.is_admin is True
```

### Authenticated Client Fixtures

```python
# Client with authenticated session
def test_protected_route(authenticated_client):
    response = authenticated_client.get("/profile")
    assert response.status_code == 200

def test_admin_route(admin_client):
    response = admin_client.get("/admin")
    assert response.status_code == 200
```

### Data Fixtures

```python
# Pre-created test data
def test_tournament(test_tournament, test_lake, test_ramp):
    assert test_tournament.lake_id == test_lake.id
    assert test_tournament.ramp_id == test_ramp.id
```

---

## Writing Tests

### Test Naming Conventions

```python
# Good test names - describe what is being tested
def test_login_with_valid_credentials():
    pass

def test_login_fails_with_invalid_password():
    pass

def test_member_can_vote_in_poll():
    pass

def test_non_member_cannot_vote_in_poll():
    pass
```

### Test Structure (AAA Pattern)

```python
def test_user_registration():
    # Arrange - Set up test data
    email = "newuser@example.com"
    password = "SecurePassword123!"

    # Act - Perform the action
    response = client.post("/register", data={
        "first_name": "New",
        "last_name": "User",
        "email": email,
        "password": password,
    })

    # Assert - Verify the result
    assert response.status_code == 302
    user = db.query(Angler).filter(Angler.email == email).first()
    assert user is not None
    assert user.name == "New User"
```

### Testing with Markers

```python
import pytest

@pytest.mark.unit
def test_password_validation():
    pass

@pytest.mark.integration
def test_database_query():
    pass

@pytest.mark.routes
def test_login_endpoint():
    pass

@pytest.mark.security
def test_csrf_protection():
    pass

@pytest.mark.slow
def test_large_dataset_processing():
    pass

# Skip in CI environment
@pytest.mark.skip_ci
def test_external_api_integration():
    pass
```

---

## Coverage Reports

### Generate Coverage Report

```bash
# Run tests with coverage
nix develop -c run-tests --coverage

# Open HTML report
open htmlcov/index.html

# View terminal report
pytest --cov=. --cov-report=term-missing
```

### Coverage Targets

| Category | Target | Current |
|----------|--------|---------|
| Overall | >80% | 85% |
| Core Auth | >90% | 92% |
| Routes | >85% | 88% |
| Query Service | >90% | 91% |
| Security | >95% | 96% |

### Coverage Configuration

Coverage settings in `pytest.ini`:

```ini
[coverage:run]
source = .
omit =
    */tests/*
    */test_*
    */__pycache__/*
    */venv/*
    */.nix-python-packages/*
    */scripts/*

[coverage:report]
precision = 2
show_missing = True
fail_under = 80  # CI fails if below 80%
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### Pre-commit Hook

```bash
# Install pre-commit hooks
pre-commit install

# Run tests before commit
cat > .git/hooks/pre-push <<EOF
#!/bin/bash
echo "Running tests before push..."
nix develop -c run-tests
EOF

chmod +x .git/hooks/pre-push
```

---

## Debugging Tests

### Run Specific Test

```bash
# Run single test file
pytest tests/unit/test_auth_helpers.py -v

# Run single test class
pytest tests/unit/test_auth_helpers.py::TestAuthHelpers -v

# Run single test function
pytest tests/unit/test_auth_helpers.py::TestAuthHelpers::test_login_success -v
```

### Debug Mode

```bash
# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest --showlocals

# Enter debugger on failure
pytest --pdb

# Verbose output
pytest -vv
```

### Print Debugging

```python
def test_something(capsys):
    print("Debug output")
    result = function_under_test()
    captured = capsys.readouterr()
    assert "expected" in captured.out
```

---

## Performance Testing

### Measure Test Execution Time

```bash
# Show slowest tests
pytest --durations=10

# Profile tests
pytest --profile

# Run only fast tests
pytest -m "not slow"
```

### Parallel Test Execution

```bash
# Run tests in parallel (uses all CPU cores)
pytest -n auto

# Or with coverage
pytest -n auto --cov=. --cov-report=html
```

---

## Common Testing Patterns

### Testing Authentication

```python
def test_protected_route_requires_auth(client):
    response = client.get("/profile")
    assert response.status_code in [302, 303]
    assert "/login" in response.headers["location"]

def test_protected_route_with_auth(authenticated_client):
    response = authenticated_client.get("/profile")
    assert response.status_code == 200
```

### Testing Forms

```python
def test_form_submission(client, db_session):
    response = client.post("/submit", data={
        "field1": "value1",
        "field2": "value2",
    })
    assert response.status_code == 302

    # Verify database was updated
    record = db_session.query(Model).first()
    assert record.field1 == "value1"
```

### Testing CSRF

```python
def test_csrf_token_required(client):
    response = client.post("/submit", data={
        "field": "value"
        # Missing CSRF token
    })
    assert response.status_code == 403

def test_csrf_token_valid(client):
    csrf_token = get_csrf_token(client)
    response = client.post("/submit", data={
        "field": "value",
        "csrf_token": csrf_token,
    })
    assert response.status_code in [200, 302]
```

### Testing Database Transactions

```python
def test_rollback_on_error(db_session):
    user = Angler(name="Test")
    db_session.add(user)

    try:
        # Cause an error
        raise Exception("Test error")
        db_session.commit()
    except:
        db_session.rollback()

    # Verify nothing was saved
    count = db_session.query(Angler).count()
    assert count == 0
```

---

## Troubleshooting

### Tests Failing Locally But Passing in CI

- Check environment variables
- Check database state (clean slate in CI)
- Check file paths (absolute vs relative)
- Check timezone settings

### Tests Passing Locally But Failing in CI

- Check for test order dependencies
- Run tests with `pytest --randomly` to catch dependencies
- Check for missing test dependencies in requirements-test.txt
- Check for hardcoded local paths

### Slow Tests

- Mark slow tests with `@pytest.mark.slow`
- Run fast tests during development: `pytest -m "not slow"`
- Use test parallelization: `pytest -n auto`
- Check for unnecessary database operations
- Mock external services

### Flaky Tests

- Tests that pass/fail inconsistently
- Usually caused by:
  - Race conditions
  - Time-dependent tests
  - External service dependencies
  - Test order dependencies
- Fix by:
  - Adding proper fixtures
  - Mocking time-dependent functions
  - Ensuring test isolation
  - Using `pytest --randomly` to catch issues

---

## Best Practices

### ✅ DO

- Write tests for all new features
- Test both success and failure cases
- Test edge cases and boundaries
- Use descriptive test names
- Keep tests independent and isolated
- Mock external services
- Use fixtures for common setup
- Run tests before committing
- Aim for >80% coverage

### ❌ DON'T

- Skip writing tests ("I'll do it later")
- Test implementation details
- Share state between tests
- Use real external services in tests
- Commit code with failing tests
- Ignore flaky tests
- Write overly complex tests
- Test framework code (e.g., FastAPI itself)

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing Guide](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Last Updated**: 2025-10-19
**Test Status**: 219 passing, 2 skipped
