# Contributing to SABC Tournament Management System

Thank you for your interest in contributing to the South Austin Bass Club Tournament Management System! This guide will help you get started with development and ensure your contributions align with our project standards.

## 🎯 Project Goals

Our primary objectives are:

- **Type Safety First** - Comprehensive type annotations throughout the codebase
- **Minimal Complexity** - Simplest solution that meets requirements
- **Performance** - Sub-200ms response times for all operations
- **Maintainability** - Clean, well-documented code that's easy to understand
- **Security** - Robust authentication and data protection

## 🚀 Getting Started

### Prerequisites

- **Nix** (strongly recommended) for reproducible development environment
- **Git** for version control
- **Basic Python knowledge** (FastAPI, SQLAlchemy, Jinja2)
- **PostgreSQL understanding** for database work

### Development Environment Setup

#### Option 1: Nix (Recommended)

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
```

#### Option 2: Manual Setup

```bash
# Clone and setup
git clone https://github.com/envasquez/SABC.git
cd SABC

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL
createdb sabc
export DATABASE_URL="postgresql://username:password@localhost:5432/sabc"

# Initialize database
python scripts/setup_db.py
python scripts/setup_admin.py

# Start server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## 📋 Development Workflow

### 1. Before You Start

- **Read the documentation** - CLAUDE.md, README.md, and this file
- **Understand the architecture** - FastAPI + PostgreSQL + type safety
- **Check existing issues** - Look for similar work or bugs
- **Open an issue** - Discuss major changes before implementing

### 2. Making Changes

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes following our standards
# (See Code Standards section below)

# Test your changes
nix develop -c run-tests

# Format and check code quality
nix develop -c format-code
nix develop -c check-code
```

### 3. Submission Process

```bash
# Commit your changes
git add .
git commit -m "feat: descriptive commit message"

# Push to your fork
git push origin feature/your-feature-name

# Open a pull request on GitHub
```

## 📖 Code Standards

### Type Safety Requirements

**ALL Python code MUST have comprehensive type annotations:**

```python
# ✅ REQUIRED - Proper type annotations
from typing import Any, Dict, List, Optional, Union

def process_tournament_results(
    tournament_id: int,
    results: List[Dict[str, Any]]
) -> Optional[Dict[str, Union[int, float]]]:
    """Process tournament results with complete type safety."""
    if not results:
        return None

    total_weight = sum(result.get("weight", 0.0) for result in results)
    return {
        "tournament_id": tournament_id,
        "total_participants": len(results),
        "total_weight": total_weight
    }

# ❌ FORBIDDEN - No type annotations
def process_tournament_results(tournament_id, results):
    if not results:
        return None
    total_weight = sum(result.get("weight", 0.0) for result in results)
    return {"tournament_id": tournament_id, "total_participants": len(results)}
```

### Import Standards

**Never use wildcard imports:**

```python
# ✅ CORRECT - Explicit imports
from fastapi import FastAPI, Request, HTTPException, Depends
from typing import Any, Dict, List, Optional
from sqlalchemy import text

# ❌ FORBIDDEN - Wildcard imports
from fastapi import *
from typing import *
```

### Database Patterns

**Use type-safe database operations:**

```python
# ✅ CORRECT - Type-safe database query
from core.database import db
from typing import List, Dict, Any

def get_tournament_standings(tournament_id: int) -> List[Dict[str, Any]]:
    """Get tournament standings with proper typing."""
    return db("""
        SELECT
            a.name,
            r.total_weight,
            r.points,
            r.place
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        ORDER BY r.place ASC
    """, {"tournament_id": tournament_id})

# ❌ AVOID - Untyped queries
def get_standings(id):
    return db(f"SELECT * FROM results WHERE tournament_id = {id}")
```

### FastAPI Route Patterns

**Use proper route type annotations:**

```python
# ✅ CORRECT - Fully typed route
from typing import Union
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import TemplateResponse

@router.get("/tournaments/{tournament_id}")
async def view_tournament(
    request: Request,
    tournament_id: int
) -> Union[RedirectResponse, TemplateResponse]:
    """View tournament details with proper type safety."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")

    tournament = get_tournament_by_id(tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    return templates.TemplateResponse("tournament.html", {
        "request": request,
        "user": user,
        "tournament": tournament
    })
```

### Error Handling

**Use consistent error handling patterns:**

```python
# ✅ CORRECT - Proper error handling
from core.helpers.response import error_redirect
from core.helpers.logging_config import get_logger

logger = get_logger(__name__)

@router.post("/admin/tournaments/create")
async def create_tournament(request: Request, data: TournamentCreateForm) -> RedirectResponse:
    """Create tournament with proper error handling."""
    if not (user := require_admin(request)):
        return RedirectResponse("/login")

    try:
        tournament_id = db("""
            INSERT INTO tournaments (event_id, lake_id, ramp_id, entry_fee)
            VALUES (:event_id, :lake_id, :ramp_id, :entry_fee)
        """, {
            "event_id": data.event_id,
            "lake_id": data.lake_id,
            "ramp_id": data.ramp_id,
            "entry_fee": data.entry_fee
        })

        logger.info(f"Tournament created with ID {tournament_id} by user {user['id']}")
        return RedirectResponse(f"/admin/tournaments?success=Tournament created successfully")

    except Exception as e:
        logger.error(f"Failed to create tournament: {e}", exc_info=True)
        return error_redirect("/admin/tournaments", "Failed to create tournament. Please try again.")
```

## 🧪 Testing Requirements

### Test Coverage

All contributions MUST include appropriate tests:

- **Unit tests** for business logic functions
- **Route tests** for HTTP endpoints
- **Integration tests** for database operations
- **Auth tests** for permission checking

### Test Examples

```python
# Unit test example
def test_calculate_tournament_points():
    """Test point calculation logic."""
    results = [
        {"place": 1, "total_weight": 15.5},
        {"place": 2, "total_weight": 14.2},
        {"place": 3, "total_weight": 13.8}
    ]

    points = calculate_points(results)

    assert points[0]["points"] == 100  # 1st place
    assert points[1]["points"] == 99   # 2nd place
    assert points[2]["points"] == 98   # 3rd place

# Route test example
def test_tournament_creation_requires_admin(client, test_user):
    """Test that tournament creation requires admin privileges."""
    response = client.post("/admin/tournaments/create", json={
        "event_id": 1,
        "lake_id": 1,
        "ramp_id": 1,
        "entry_fee": 25.00
    })

    assert response.status_code == 403
```

### Running Tests

```bash
# Run all tests
nix develop -c run-tests

# Run specific test categories
nix develop -c test-backend      # Backend only
nix develop -c test-frontend     # Frontend only
nix develop -c test-integration  # Integration tests

# Run with coverage
nix develop -c test-coverage
```

## 📝 Documentation Standards

### Code Documentation

**All functions and classes must have docstrings:**

```python
def calculate_aoy_standings(year: int) -> List[Dict[str, Any]]:
    """
    Calculate Angler of the Year standings for a given year.

    Args:
        year: The tournament year to calculate standings for

    Returns:
        List of angler standings with points, tournaments, and rankings

    Raises:
        ValueError: If year is invalid or no tournaments found
    """
    # Implementation here
```

### Commit Message Format

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(polls): add tournament location voting system
fix(auth): resolve session timeout issue
docs(contributing): update development setup instructions
```

## 🔍 Code Review Process

### Before Submitting

- [ ] **Code formatted**: `nix develop -c format-code`
- [ ] **Linting passes**: `nix develop -c check-code`
- [ ] **Type checking passes**: Zero MyPy errors
- [ ] **Tests pass**: `nix develop -c run-tests`
- [ ] **Documentation updated**: If adding features
- [ ] **Performance tested**: No regression in response times

### Pull Request Requirements

Your PR must include:

1. **Clear description** of changes and motivation
2. **Test coverage** for new functionality
3. **Documentation updates** if needed
4. **Type annotations** for all new code
5. **No breaking changes** unless discussed first

### Review Criteria

Reviewers will check for:

- **Type safety** - All code properly typed
- **Performance** - No significant slowdowns
- **Security** - No new vulnerabilities
- **Maintainability** - Code is clean and understandable
- **Test coverage** - Adequate testing of changes
- **Documentation** - Clear and up-to-date docs

## 🛠️ Development Tips

### Common Patterns

#### Database Queries
```python
# Use the centralized query service
from core.query_service import QueryService

with engine.connect() as conn:
    qs = QueryService(conn)
    results = qs.fetch_all("SELECT * FROM tournaments WHERE year = :year", {"year": 2024})
```

#### Authentication
```python
# Use typed auth helpers
from core.helpers.auth import require_admin, require_member

@router.post("/admin/action")
async def admin_action(request: Request) -> RedirectResponse:
    user = require_admin(request)  # Raises exception if not admin
    # Implementation here
```

#### Error Handling
```python
# Use consistent error responses
from core.helpers.response import error_redirect

try:
    # Database operation
    result = db("INSERT INTO ...", params)
    return RedirectResponse("/success")
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return error_redirect("/form", "Operation failed. Please try again.")
```

### Performance Guidelines

- **Database queries** should be optimized with proper indexes
- **Template rendering** should cache where possible
- **API responses** should be under 200ms for most operations
- **Memory usage** should remain under 100MB per instance

### Security Checklist

- [ ] **Input validation** using Pydantic models
- [ ] **SQL injection protection** via parameterized queries
- [ ] **XSS prevention** through template escaping
- [ ] **Authentication required** for protected operations
- [ ] **Authorization checked** for admin-only functions
- [ ] **Sensitive data protected** (passwords, tokens, etc.)

## 🐛 Reporting Issues

### Bug Reports

When reporting bugs, include:

- **Clear description** of the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Error logs** if available

### Feature Requests

For new features, provide:

- **Use case description** - why is this needed?
- **Proposed solution** - how should it work?
- **Alternatives considered** - other approaches
- **Implementation complexity** - rough estimate

## 📞 Getting Help

### Resources

- **Documentation**: README.md and CLAUDE.md
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs) when running
- **Issues**: GitHub issues for bugs and features
- **Discussions**: GitHub discussions for questions

### Contact

- **GitHub Issues**: Technical problems and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Email**: For sensitive issues or private discussions

## 🏆 Recognition

Contributors will be recognized in:

- **CHANGELOG.md** for significant contributions
- **README.md** contributors section
- **Release notes** for major features

We appreciate all contributions, from bug reports to major features!

---

## Quick Reference

### Essential Commands
```bash
nix develop              # Enter development environment
setup-db                 # Initialize database
start-app               # Start development server
format-code             # Format code with ruff
check-code              # Run type checking and linting
run-tests               # Run complete test suite
```

### Quality Checklist
- [ ] Type annotations on all functions
- [ ] No wildcard imports
- [ ] Proper error handling
- [ ] Tests for new functionality
- [ ] Documentation updated
- [ ] Performance considerations
- [ ] Security review completed

**Thank you for contributing to SABC Tournament Management System!** 🎣