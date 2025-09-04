# CI Status Badge

Add this badge to your README.md to show CI status:

```markdown
[![CI Pipeline](https://github.com/envasquez/SABC/actions/workflows/ci.yml/badge.svg)](https://github.com/envasquez/SABC/actions/workflows/ci.yml)
```

The badge will show:
- ✅ Green "passing" when all tests pass
- ❌ Red "failing" when any tests fail
- 🟡 Yellow "pending" when tests are running

## What the CI Pipeline Tests

### 🧪 **Test Matrix**
- Python 3.11 and 3.12 compatibility
- Cross-version dependency compatibility

### 🔍 **Code Quality**
- **Linting**: Ruff code style and error detection
- **Type Checking**: MyPy static type analysis
- **Security**: Safety vulnerability scanning + Bandit security analysis

### 🧪 **Test Coverage**
- **Backend Tests**: API endpoints, database operations, business logic
- **Frontend Tests**: Browser automation with Playwright (headless)
- **Integration Tests**: End-to-end user workflows
- **Coverage Reporting**: Uploaded to Codecov

### 🚀 **Build Validation**
- **Application Startup**: Verifies server starts successfully
- **Health Check**: Tests `/health` endpoint functionality
- **Deployment Package**: Creates production-ready build artifact

### 📊 **Artifacts**
Each CI run generates:
- Test reports (HTML format)
- Coverage reports
- Security scan results
- Deployment package (`.tar.gz`)

## CI Triggers

The pipeline runs on:
- Every push to `master` branch
- Every pull request to `master` branch
- Manual workflow dispatch

## Local Testing

To run the same checks locally:
```bash
nix develop
test-backend      # Backend tests
test-frontend     # Frontend tests  
test-coverage     # Coverage report
check-code        # Linting + type checking
```