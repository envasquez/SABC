# Development Guide - SABC Tournament Management

## Overview

This guide provides everything you need to set up a development environment and start contributing to the SABC Tournament Management System.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Environment](#development-environment)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Code Standards](#code-standards)
6. [Database Development](#database-development)
7. [Frontend Development](#frontend-development)
8. [Testing](#testing)
9. [Debugging](#debugging)
10. [Common Tasks](#common-tasks)

---

## Quick Start

### Using Nix (Recommended)

```bash
# Clone the repository
git clone https://github.com/envasquez/SABC.git
cd SABC

# Enter development environment
nix develop

# Initialize database
setup-db

# Start development server
start-app

# Open in browser
open http://localhost:8000
```

### Manual Setup

```bash
# Clone repository
git clone https://github.com/envasquez/SABC.git
cd SABC

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL (macOS with Homebrew)
brew install postgresql@17
brew services start postgresql@17
createdb sabc

# Configure environment
export DATABASE_URL="postgresql://$(whoami)@localhost:5432/sabc"
export SECRET_KEY="development-secret-key-change-in-production"

# Initialize database
python scripts/setup_db.py
python scripts/setup_admin.py

# Start server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

---

## Development Environment

### Nix Environment

The Nix development environment provides:
- Python 3.11 with all dependencies
- PostgreSQL 17
- Pre-configured environment variables
- Development commands

#### Available Commands

| Command | Description |
|---------|-------------|
| `start-app` | Start FastAPI development server |
| `setup-db` | Initialize PostgreSQL database |
| `reset-db` | Reset database (destructive) |
| `format-code` | Auto-format Python code with Ruff |
| `check-code` | Run type checking and linting |
| `run-tests` | Run complete test suite |
| `deploy-app` | Run all deployment checks |

### IDE Setup

#### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance (type checking)
- Ruff (linting/formatting)
- Jinja (template syntax)
- GitLens

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "ruff.lint.args": ["--config=pyproject.toml"]
}
```

#### PyCharm

1. Open project directory
2. Configure Python interpreter (use Nix or venv)
3. Enable Ruff plugin for linting
4. Set Jinja2 for template files

---

## Project Structure

```
SABC/
├── app.py                    # Application entry point
├── core/                     # Core business logic
│   ├── db_schema/           # Database models
│   ├── query_service/       # Database queries
│   ├── helpers/             # Utility functions
│   ├── email/               # Email service
│   └── monitoring/          # Sentry/Prometheus
├── routes/                   # FastAPI routes
│   ├── auth/                # Authentication
│   ├── pages/               # Public pages
│   ├── admin/               # Admin routes
│   ├── voting/              # Poll voting
│   └── tournaments/         # Tournament management
├── templates/                # Jinja2 templates
├── static/                   # CSS, JavaScript
├── tests/                    # Test suite
├── alembic/                  # Database migrations
└── docs/                     # Documentation
```

### Key Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI application setup |
| `core/db_schema/models.py` | SQLAlchemy ORM models |
| `core/deps.py` | Dependency injection |
| `templates/base.html` | Base layout template |
| `templates/macros.html` | Reusable Jinja2 macros |
| `static/utils.js` | Shared JavaScript utilities |

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout master
git pull origin master
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the code standards (see below). Key principles:
- Add type annotations to all functions
- Use existing components and helpers
- Write tests for new functionality

### 3. Quality Checks

**Before every commit:**

```bash
# Format code
nix develop -c format-code

# Type check and lint
nix develop -c check-code

# Run tests
nix develop -c run-tests
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add tournament statistics endpoint"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Code refactoring
- `test:` - Test additions/changes

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
# Create pull request on GitHub
```

---

## Code Standards

### Type Annotations

**Required on all functions:**

```python
# ✅ Correct
from typing import Optional, List, Dict, Any

def get_tournament_results(
    tournament_id: int,
    include_teams: bool = False
) -> List[Dict[str, Any]]:
    """Get tournament results."""
    ...

# ❌ Incorrect - no type annotations
def get_tournament_results(tournament_id, include_teams=False):
    ...
```

### Import Standards

```python
# ✅ Correct - explicit imports
from fastapi import Request, HTTPException
from typing import Optional, List

# ❌ Incorrect - wildcard imports
from fastapi import *
from typing import *
```

### Route Patterns

```python
from typing import Union
from fastapi import Request
from fastapi.responses import RedirectResponse, TemplateResponse

@router.get("/example")
async def example_route(
    request: Request
) -> Union[RedirectResponse, TemplateResponse]:
    """Route with proper return type."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    return templates.TemplateResponse("example.html", {
        "request": request,
        "user": user
    })
```

### Error Handling

```python
from core.helpers.response import error_redirect
from core.helpers.logging import get_logger

logger = get_logger(__name__)

@router.post("/action")
async def action_route(request: Request) -> RedirectResponse:
    try:
        # Business logic here
        return RedirectResponse("/success")
    except Exception as e:
        logger.error(f"Action failed: {e}")
        return error_redirect("/form", "Action failed. Please try again.")
```

---

## Database Development

### Working with Models

```python
from core.db_schema import get_session, Angler, Tournament

# Read operations
with get_session() as session:
    anglers = session.query(Angler).filter(Angler.member == True).all()

# Write operations
with get_session() as session:
    angler = Angler(name="John Doe", email="john@example.com")
    session.add(angler)
    session.commit()
```

### Creating Migrations

```bash
# After modifying models.py
nix develop -c alembic revision --autogenerate -m "Add new column"

# Review the migration file
cat alembic/versions/xxx_add_new_column.py

# Apply migration
nix develop -c alembic upgrade head
```

### Database Reset

```bash
# Complete reset (development only)
nix develop -c reset-db

# Or manually
dropdb sabc
createdb sabc
python scripts/setup_db.py
python scripts/setup_admin.py
```

---

## Frontend Development

### Jinja2 Templates

**Using Macros:**

```jinja2
{% from "macros.html" import csrf_token, form_field, alert, card %}

{# CSRF token in forms #}
<form method="POST">
    {{ csrf_token(request) }}
    {{ form_field('Name', 'name', required=True) }}
    <button type="submit">Submit</button>
</form>

{# Cards #}
{% call card(title='Results', header_class='bg-success text-white') %}
    <p>Card content here</p>
{% endcall %}
```

**Template Inheritance:**

```jinja2
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
    <h1>Page Content</h1>
{% endblock %}

{% block extra_js %}
    <script src="/static/page-specific.js"></script>
{% endblock %}
```

### JavaScript Development

**Using Shared Utilities (`static/utils.js`):**

```javascript
// CSRF token for AJAX
const csrfToken = getCsrfToken();

// Show toast notification
showToast('Saved successfully', 'success');

// Fetch with retry
const response = await fetchWithRetry('/api/data');

// Delete confirmation
const deleteManager = new DeleteConfirmationManager({
    modalId: 'deleteModal',
    deleteUrlTemplate: (id) => `/admin/items/${id}`,
    onSuccess: () => location.reload()
});
```

### HTMX Patterns

```html
<!-- Load content dynamically -->
<div hx-get="/api/results" hx-trigger="load" hx-swap="innerHTML">
    Loading...
</div>

<!-- Form submission with response -->
<form hx-post="/api/vote" hx-swap="outerHTML">
    {{ csrf_token(request) }}
    <button type="submit">Vote</button>
</form>

<!-- Polling for updates -->
<div hx-get="/api/poll-status" hx-trigger="every 5s">
    Status: Active
</div>
```

### CSS Styling

The project uses:
- **Bootstrap 5** - UI framework
- **Bootswatch Darkly** - Dark theme
- **Custom CSS** - `static/style.css`

```css
/* Add custom styles to static/style.css */
.custom-component {
    /* Use Bootstrap variables when possible */
    background-color: var(--bs-dark);
    color: var(--bs-light);
}
```

---

## Testing

### Running Tests

```bash
# All tests
nix develop -c run-tests

# Specific test file
pytest tests/unit/test_auth_helpers.py -v

# Specific test
pytest tests/unit/test_auth_helpers.py::test_login_success -v

# With coverage
pytest --cov=core --cov-report=html
```

### Writing Tests

**Unit Test Example:**

```python
def test_calculate_points():
    """Test tournament point calculation."""
    results = [
        {"place": 1, "total_weight": 15.5},
        {"place": 2, "total_weight": 14.2},
    ]

    points = calculate_points(results)

    assert points[0]["points"] == 100
    assert points[1]["points"] == 99
```

**Route Test Example:**

```python
def test_protected_route_requires_auth(client):
    """Test that protected routes require authentication."""
    response = client.get("/profile")

    assert response.status_code in [302, 303]
    assert "/login" in response.headers["location"]
```

**Fixture Usage:**

```python
def test_member_can_vote(authenticated_client, test_poll):
    """Test that members can vote in polls."""
    response = authenticated_client.post(
        f"/polls/{test_poll.id}/vote",
        data={"option_id": test_poll.options[0].id}
    )

    assert response.status_code == 302
```

---

## Debugging

### Debug Logging

```python
from core.helpers.logging import get_logger

logger = get_logger(__name__)

def some_function():
    logger.debug("Entering function")
    logger.info("Processing data")
    logger.warning("Unusual condition")
    logger.error("Something went wrong")
```

### Interactive Debugging

```python
# Add breakpoint in code
breakpoint()  # Python 3.7+

# Or
import pdb; pdb.set_trace()
```

### Database Debugging

```bash
# Connect to database
docker compose exec db psql -U sabc

# Or with Nix
psql $DATABASE_URL

# Useful queries
SELECT * FROM anglers LIMIT 10;
SELECT * FROM alembic_version;
```

### Request Debugging

```python
@router.get("/debug")
async def debug_route(request: Request):
    """Debug endpoint (development only)."""
    return {
        "headers": dict(request.headers),
        "cookies": dict(request.cookies),
        "query_params": dict(request.query_params),
        "session": dict(request.session),
    }
```

---

## Common Tasks

### Adding a New Route

1. Create route file in appropriate directory:
   ```python
   # routes/pages/new_page.py
   from fastapi import APIRouter, Request
   from fastapi.templating import TemplateResponse

   router = APIRouter()

   @router.get("/new-page")
   async def new_page(request: Request) -> TemplateResponse:
       return templates.TemplateResponse("new_page.html", {
           "request": request
       })
   ```

2. Register in parent router or `app.py`

3. Create template in `templates/new_page.html`

### Adding a Database Column

1. Update model in `core/db_schema/models.py`:
   ```python
   class Angler(Base):
       # ... existing columns ...
       new_column = Column(String(100), nullable=True)
   ```

2. Generate migration:
   ```bash
   alembic revision --autogenerate -m "Add new_column to anglers"
   ```

3. Review and apply migration:
   ```bash
   alembic upgrade head
   ```

### Adding a New Helper Function

1. Add to appropriate file in `core/helpers/`:
   ```python
   # core/helpers/new_helper.py
   from typing import Optional

   def new_helper_function(param: str) -> Optional[str]:
       """
       Helper function description.

       Args:
           param: Description of parameter

       Returns:
           Description of return value
       """
       # Implementation
   ```

2. Add tests in `tests/unit/test_new_helper.py`

### Adding a JavaScript Utility

1. Add to `static/utils.js`:
   ```javascript
   /**
    * Description of function
    * @param {string} param - Parameter description
    * @returns {string} Return description
    */
   function newUtility(param) {
       // Implementation
   }

   // Export for global access
   window.newUtility = newUtility;
   ```

2. Use in templates:
   ```html
   <script>
       const result = newUtility('value');
   </script>
   ```

---

## Environment Variables (Development)

Create `.env.local` for development overrides:

```bash
# Database (local PostgreSQL)
DATABASE_URL=postgresql://localhost/sabc

# Security (use simple key for development)
SECRET_KEY=dev-secret-key-not-for-production

# Email (optional - can use console backend)
SMTP_HOST=localhost
SMTP_PORT=1025  # MailHog port

# Disable external services
SENTRY_DSN=

# Debug mode
DEBUG=true
LOG_LEVEL=DEBUG
```

---

## Troubleshooting

### Import Errors

```bash
# Ensure you're in the Nix environment
nix develop

# Or activate virtual environment
source venv/bin/activate
```

### Database Connection Failed

```bash
# Check PostgreSQL is running
pg_isready

# Check DATABASE_URL
echo $DATABASE_URL

# Reset database
nix develop -c reset-db
```

### Type Checking Errors

```bash
# Run MyPy for specific file
mypy core/helpers/auth.py

# Fix common issues:
# - Add type annotations
# - Import types from typing module
# - Use Optional for nullable values
```

### Test Failures

```bash
# Run with verbose output
pytest -vv --tb=long

# Run specific failing test
pytest tests/unit/test_auth.py::test_login -vv
```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [TESTING.md](TESTING.md) - Testing guide
- [COMPONENTS.md](COMPONENTS.md) - Component reference
- [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md) - Migration guide

---

**Last Updated**: 2024-11-30
