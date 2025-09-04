# SABC Application Test Suite

Comprehensive testing framework for the South Austin Bass Club (SABC) tournament management system.

## Overview

This test suite provides complete coverage for both backend API functionality and frontend user interactions, ensuring the reliability and quality of the SABC application.

## Test Categories

### Backend Tests (`test_backend.py`)
- **Authentication**: User registration, login, logout, permissions
- **Events**: Tournament and holiday event management
- **Polls**: Poll creation, voting, results calculation
- **Tournaments**: Tournament lifecycle, results entry, points calculation
- **News**: News article management and display
- **Database**: Data integrity, constraints, relationships
- **Security**: SQL injection prevention, XSS protection, CSRF protection
- **Business Logic**: Tournament payouts, scoring calculations

### Frontend Tests (`test_frontend.py`)
- **Navigation**: Page routing, responsive menus
- **Authentication**: Login/logout UI flows
- **Event Management**: Admin interface for events
- **Polls**: Voting interface, results visualization
- **Calendar**: Event display and navigation
- **Tournaments**: Results display, standings
- **News**: Admin news management
- **Accessibility**: WCAG compliance, keyboard navigation
- **Responsive Design**: Mobile and desktop layouts
- **Performance**: Load times, JavaScript errors

### Integration Tests (`test_integration.py`)
- **Complete User Workflows**: End-to-end user journeys
- **Data Consistency**: Cross-page data verification
- **System Limits**: Performance under load
- **Concurrent Usage**: Multiple user scenarios

## Quick Start

### 1. Install Dependencies
```bash
make install
```

### 2. Set Up Development Environment
```bash
make setup-dev
```

### 3. Run All Tests
```bash
make test
```

## Test Commands

### Basic Testing
```bash
# Run all tests
make test

# Backend tests only
make test-backend

# Frontend tests only
make test-frontend

# Integration tests only
make test-integration

# Quick test subset (excludes slow tests)
make test-quick
```

### Specific Test Categories
```bash
# Performance tests
make test-performance

# Security tests
make test-security

# Accessibility tests
make test-accessibility
```

### Advanced Usage
```bash
# Run with coverage report
make coverage

# Run specific test filter
make test-filter

# Run tests in parallel
make test-parallel

# Watch tests during development
make watch-tests
```

## Test Configuration

### Environment Variables
- `DATABASE_URL`: Test database connection string
- `TEST_SERVER_PORT`: Port for test server (default: 8000)
- `HEADLESS_TESTS`: Run frontend tests without browser UI (default: true)

### Configuration Files
- `pytest.ini`: Pytest configuration and markers
- `conftest.py`: Shared fixtures and test setup
- `test_requirements.txt`: Testing dependencies

## Test Data

The test suite automatically creates and manages test data:

### Test Users
- **Admin User**: `admin@test.com` / `adminpass`
- **Member User**: `member@test.com` / `memberpass` 
- **Guest User**: `guest@test.com` / `guestpass`

### Test Events
- Sample tournaments across different dates
- Federal holidays for calendar testing
- Various event types and configurations

### Test Database
- Isolated test database created for each test run
- Automatic cleanup after tests complete
- Sample data populated automatically

## Running Specific Tests

### By Test Class
```bash
# Test authentication only
python -m pytest test_backend.py::TestAuthentication -v

# Test frontend navigation
python -m pytest test_frontend.py::TestNavigation -v
```

### By Test Method
```bash
# Test specific login functionality
python -m pytest test_backend.py::TestAuthentication::test_login_valid_credentials -v
```

### By Markers
```bash
# Run only slow tests
python -m pytest -m slow

# Run only integration tests
python -m pytest -m integration

# Exclude slow tests
python -m pytest -m "not slow"
```

## Test Reports

After running tests, several reports are generated:

### Coverage Report
- **HTML**: `htmlcov/index.html` - Interactive coverage report
- **Terminal**: Coverage summary displayed after test run

### Test Reports
- **Backend**: `backend_test_report.html` - Detailed backend test results
- **Frontend**: `frontend_test_report.html` - Frontend test results with screenshots
- **Summary**: `test_report.md` - Overall test summary

### JUnit XML
- `backend_results.xml` - For CI/CD integration
- `frontend_results.xml` - For CI/CD integration

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    - run: make install
    - run: make ci-test
```

### Local CI Simulation
```bash
# Run the same tests as CI
make ci-test
```

## Browser Testing

Frontend tests use Playwright for cross-browser testing:

### Supported Browsers
- Chromium (default)
- Firefox (with `--browser firefox`)
- WebKit/Safari (with `--browser webkit`)

### Headed vs Headless
```bash
# Run with visible browser (for debugging)
python run_tests.py --frontend-only --headed

# Run headless (default)
python run_tests.py --frontend-only
```

## Performance Testing

### Load Testing
```bash
# Test with many concurrent users
make test-stress

# Performance benchmarking
make test-performance
```

### Metrics Monitored
- Page load times
- Database query performance
- Memory usage
- Network request counts

## Security Testing

### Automated Security Checks
- SQL injection prevention
- XSS (Cross-Site Scripting) protection
- CSRF (Cross-Site Request Forgery) protection
- Authentication bypass attempts
- Authorization validation

```bash
make test-security
```

## Accessibility Testing

### WCAG Compliance
- Color contrast validation
- Keyboard navigation testing
- Screen reader compatibility
- Form label associations
- Alt text verification

```bash
make test-accessibility
```

## Debugging Tests

### Debug Frontend Tests
```bash
# Run with visible browser and slow execution
python -m pytest test_frontend.py --headed --slowmo=1000 -s
```

### Debug Backend Tests
```bash
# Run with detailed output
python -m pytest test_backend.py -vvv -s
```

### Debug Integration Tests
```bash
# Run specific integration test with debugging
python -m pytest test_integration.py::TestCompleteUserWorkflows::test_member_registration_to_voting_workflow -vvv -s --headed
```

## Contributing to Tests

### Adding New Tests
1. Follow naming convention: `test_*.py`
2. Use appropriate markers: `@pytest.mark.backend`, `@pytest.mark.frontend`, etc.
3. Include docstrings explaining test purpose
4. Use existing fixtures when possible

### Test Guidelines
- **Arrange, Act, Assert**: Structure tests clearly
- **Isolation**: Each test should be independent
- **Descriptive Names**: Test names should explain what they verify
- **Edge Cases**: Test boundary conditions and error scenarios
- **Performance**: Mark slow tests with `@pytest.mark.slow`

### Example Test Structure
```python
@pytest.mark.backend
def test_create_event_with_valid_data(self, admin_client, sample_event_data):
    """Test that admins can create events with valid data."""
    # Arrange
    event_data = sample_event_data
    
    # Act
    response = admin_client.post("/admin/events/create", data=event_data)
    
    # Assert
    assert response.status_code == 302
    assert "success" in response.headers.get("location", "").lower()
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Reset test database
make db-reset
```

#### Frontend Tests Timing Out
```bash
# Increase timeout in conftest.py
page.set_default_timeout(60000)  # 60 seconds
```

#### Browser Not Found
```bash
# Reinstall Playwright browsers
playwright install
```

#### Permission Errors
```bash
# Fix file permissions
chmod +x run_tests.py
```

### Test Environment Issues
- Ensure test server is not already running on port 8000
- Check that all dependencies are installed
- Verify database permissions

## Maintenance

### Regular Tasks
- Update test dependencies monthly
- Review and update test data
- Monitor test performance
- Update browser versions for frontend tests

### Cleaning Up
```bash
# Clean all test artifacts
make clean

# Reset everything
make clean && make setup-dev
```

## Contact

For questions about the test suite:
- Check existing issues in the repository
- Review test documentation in code comments
- Run `make help` for command reference