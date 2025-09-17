# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
South Austin Bass Club (SABC) tournament management system - modern FastAPI application with PostgreSQL backend, designed for minimal complexity and maximum performance.

## Key Architecture Principles
- **TYPE-SAFE CODEBASE** - Comprehensive type annotations throughout
- **MINIMAL COMPLEXITY** - Simplest solution that meets requirements
- **DATABASE-FIRST** - Business logic in SQL views and queries
- **MEMBERS-ONLY VOTING** - Only verified members can participate in polls
- **ADMIN-CONTROLLED** - Critical functions require admin privileges

## Technology Stack
- **Backend**: FastAPI 0.115+ with Python 3.11+
- **Database**: PostgreSQL 17+ with SQLAlchemy Core
- **Frontend**: Jinja2 templates with HTMX for interactivity
- **Development**: Nix development environment
- **Deployment**: Digital Ocean App Platform

## CRITICAL DEVELOPMENT RULES

### 1. Type Safety Requirements
**ALL Python code MUST have proper type annotations:**

```python
# ✅ ALWAYS DO THIS
from typing import Any, Dict, List, Optional, Union

def process_data(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Process data with proper type hints."""
    if not items:
        return None
    return {"processed": len(items)}

# ❌ NEVER DO THIS
def process_data(items):
    if not items:
        return None
    return {"processed": len(items)}
```

### 2. Import Standards
**NEVER use wildcard imports:**

```python
# ❌ NEVER DO THIS
from fastapi import *
from typing import *

# ✅ ALWAYS DO THIS
from fastapi import FastAPI, Request, HTTPException
from typing import Any, Dict, Optional
```

### 3. Module Architecture
**NEVER use conditional imports or exec() patterns:**

```python
# ❌ ABSOLUTELY FORBIDDEN
try:
    from some_module import feature
    HAS_FEATURE = True
except ImportError:
    HAS_FEATURE = False

exec(open("routes.py").read())

# ✅ PROPER FASTAPI ARCHITECTURE
from routes import auth, admin, public
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(public.router)
```

## Development Workflow

### Required Environment Setup
```bash
# Enter Nix development shell
nix develop

# Available commands:
start-app        # Start FastAPI server (localhost:8000)
setup-db         # Initialize PostgreSQL database
reset-db         # Reset database (destructive)
check-code       # Run type checking and linting
format-code      # Auto-format with ruff
deploy-app       # Full deployment checks
```

### Mandatory Code Quality Process
**EVERY commit MUST pass these checks:**

```bash
# 1. Format code
nix develop -c format-code

# 2. Run all quality checks
nix develop -c check-code

# 3. Only commit if both pass
git add .
git commit -m "Your changes"
```

**If checks fail:**
- Fix all issues before committing
- Never bypass with git commit --no-verify
- Re-run checks until clean

## Database Design Principles

### PostgreSQL-First Approach
- **Business logic in SQL** - Use views, functions, triggers
- **Minimal ORM usage** - SQLAlchemy Core, not ORM
- **Type-safe queries** - Proper parameter binding
- **Performance-focused** - Optimized queries and indexes

### Schema Organization
```sql
-- Core entities
anglers (id, name, email, member, is_admin, phone)
events (id, date, name, event_type, year)
tournaments (id, event_id, lake_id, ramp_id, complete)
results (id, tournament_id, angler_id, total_weight, points)

-- Voting system
polls (id, event_id, title, poll_type, starts_at, closes_at)
poll_options (id, poll_id, option_text, option_data)
poll_votes (id, poll_id, option_id, angler_id)

-- Location data
lakes (id, name, location)
ramps (id, lake_id, name, coordinates)
```

## FastAPI Route Organization

### Modular Router Structure
```
routes/
├── __init__.py
├── dependencies.py      # Shared dependencies
├── auth.py             # Authentication routes
├── pages.py            # Public pages
├── voting.py           # Member voting
├── tournaments_public.py # Tournament results
├── awards.py           # Awards and standings
└── admin/              # Admin-only routes
    ├── core.py         # Dashboard
    ├── events.py       # Event management
    ├── polls.py        # Poll creation
    ├── tournaments.py  # Tournament management
    └── users.py        # User management
```

### Route Type Annotations
```python
from typing import Union
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import TemplateResponse

@router.get("/example")
async def example_route(request: Request) -> Union[RedirectResponse, TemplateResponse]:
    if not user := get_current_user(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse("example.html", {"request": request, "user": user})
```

## Authentication & Authorization

### User Types
- **Anonymous** - Read-only access to public content
- **Members** - Can vote in polls, view member areas
- **Admins** - Full access to management functions

### Security Implementation
```python
# Type-safe auth helpers
from core.helpers.auth import require_admin, require_member

@router.post("/admin/action")
async def admin_action(request: Request) -> RedirectResponse:
    user = require_admin(request)  # Raises HTTPException if not admin
    # Admin logic here
    return RedirectResponse("/admin")
```

## Poll System Architecture

### Poll Types & Data Structure
```python
# Tournament location polls - structured data
option_data = {
    "lake_id": 1,
    "ramp_id": 3,
    "start_time": "06:00",
    "end_time": "15:00"
}

# Simple polls - no structured data
option_data = {}  # Uses option_text only
```

### JSON Usage Guidelines
**Minimize JSON usage - only where essential:**
- ✅ Poll option_data for tournament locations
- ✅ Template filters for rendering
- ❌ General data storage (use proper columns)
- ❌ Configuration (use environment variables)

## UI/UX Patterns

### Template-First Design
- **Jinja2 templates** with server-side rendering
- **HTMX integration** for dynamic interactions
- **Conditional admin controls** via template logic
- **Single responsive interface** for all devices

### Admin Interface Pattern
```html
<!-- Inline admin controls -->
<div class="content">
    <h2>Tournament Results</h2>
    {% if user.is_admin %}
        <button hx-get="/admin/results/edit">Edit Results</button>
    {% endif %}
    <!-- Content here -->
</div>
```

## Testing Strategy

### Test Categories
- **Unit tests** - Core business logic
- **Integration tests** - Database operations
- **Route tests** - HTTP endpoints
- **Auth tests** - Permission checking

### Running Tests
```bash
nix develop -c run-tests        # Full test suite
nix develop -c test-backend     # Backend only
nix develop -c test-frontend    # Frontend only
nix develop -c test-coverage    # With coverage report
```

## Deployment Configuration

### Environment Variables
```bash
# Required for production
DATABASE_URL=postgresql://user:pass@host:5432/sabc
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO

# Optional
DEBUG=false
PORT=8000
```

### Digital Ocean App Platform
- Uses `.do/app.yaml` for configuration (not in git)
- Managed PostgreSQL database with auto-injected credentials
- Automatic HTTPS and domain management
- Health checks at `/health` endpoint

## Performance Requirements
- **Page load time**: < 200ms average
- **Database queries**: Optimized with proper indexes
- **Memory usage**: < 100MB per instance
- **Code size**: Minimal, well-organized modules

## Success Metrics
✅ **Type Safety**: Zero MyPy errors across codebase
✅ **Code Quality**: All Ruff checks passing
✅ **Test Coverage**: >90% for critical paths
✅ **Performance**: Sub-200ms response times
✅ **Maintainability**: Clear, documented code structure

## Common Patterns

### Database Queries
```python
from core.database import db
from typing import List, Dict, Any

def get_tournament_results(tournament_id: int) -> List[Dict[str, Any]]:
    return db("""
        SELECT a.name, r.total_weight, r.points
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        ORDER BY r.points DESC
    """, {"tournament_id": tournament_id})
```

### Error Handling
```python
from core.helpers.response import error_redirect

try:
    # Database operation
    result = db("INSERT INTO ...", params)
    return RedirectResponse("/success")
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return error_redirect("/form", "Operation failed. Please try again.")
```

## What NOT to Build
- ❌ **Separate admin interface** - Use inline controls
- ❌ **Complex user roles** - Keep member/admin binary
- ❌ **Real-time features** - Server-side rendering sufficient
- ❌ **Mobile app** - Responsive web interface only
- ❌ **Microservices** - Single FastAPI application
- ❌ **Advanced caching** - Database performance sufficient

---

**Remember**: Simplicity, type safety, and maintainability are the top priorities. When in doubt, choose the simpler, more explicit solution.