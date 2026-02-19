# System Architecture - SABC Tournament Management

## Overview

The South Austin Bass Club (SABC) Tournament Management System is a modern, type-safe web application built with FastAPI and PostgreSQL. This document describes the system architecture, design decisions, and component interactions.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Browser (HTML/CSS/JS)  │  HTMX  │  Chart.js  │  Bootstrap 5               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              FastAPI App                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Routes     │  │  Middleware  │  │  Templates   │  │   Static     │    │
│  │  (FastAPI)   │  │ (CSRF/Auth)  │  │  (Jinja2)    │  │   Assets     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │Query Service │  │    Auth      │  │    Email     │  │  Monitoring  │    │
│  │   (ORM)      │  │  Helpers     │  │   Service    │  │ (Prometheus) │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     PostgreSQL 17+ Database                           │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │  │
│  │  │  Anglers   │ │   Events   │ │   Polls    │ │   Lakes    │        │  │
│  │  │  Results   │ │ Tournaments│ │   Votes    │ │   Ramps    │        │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │    Sentry    │  │     SMTP     │  │   Let's      │                      │
│  │   (Errors)   │  │    (Email)   │  │  Encrypt     │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | FastAPI | 0.115+ | Async web framework with automatic OpenAPI docs |
| Language | Python | 3.11+ | Type-safe, performant runtime |
| ORM | SQLAlchemy | 2.0+ | Database abstraction and query building |
| Migrations | Alembic | 1.12+ | Version-controlled schema changes |
| Validation | Pydantic | 2.0+ | Request/response data validation |

### Database
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Database | PostgreSQL | 17+ | Relational data storage |
| Driver | psycopg2 | 2.9+ | PostgreSQL adapter |

### Frontend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Templates | Jinja2 | 3.1+ | Server-side rendering |
| Interactivity | HTMX | 1.9+ | Dynamic updates without JavaScript |
| Charts | Chart.js | 4.4+ | Data visualization |
| CSS Framework | Bootstrap | 5.3+ | Responsive UI components |
| Theme | Bootswatch Darkly | 5.3+ | Dark theme styling |

### Infrastructure
| Component | Technology | Purpose |
|-----------|------------|---------|
| Development | Nix | Reproducible dev environment |
| Deployment | Docker + Docker Compose | Container orchestration |
| Web Server | Nginx | Reverse proxy and SSL |
| SSL | Let's Encrypt + Certbot | Free SSL certificates |
| Hosting | Digital Ocean Droplet | VPS hosting |

### Monitoring
| Component | Technology | Purpose |
|-----------|------------|---------|
| Error Tracking | Sentry | Exception monitoring and alerts |
| Metrics | Prometheus | Application instrumentation |
| Dashboards | Grafana (optional) | Metrics visualization |

---

## Directory Structure

```
SABC/
├── app.py                          # FastAPI application entry point
│
├── core/                           # Core business logic
│   ├── __init__.py
│   ├── database.py                 # Database connection factory
│   ├── deps.py                     # FastAPI dependency injection
│   ├── enums.py                    # Shared enumerations
│   │
│   ├── db_schema/                  # Database models and schema
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   └── session.py              # Session management (get_session)
│   │
│   ├── query_service/              # Centralized query service
│   │   ├── __init__.py
│   │   ├── base.py                 # Base query service class
│   │   ├── dialect_helpers.py      # PostgreSQL/SQLite compatibility
│   │   ├── event_queries.py        # Event queries
│   │   ├── event_queries_admin.py  # Admin event queries
│   │   ├── tournament_queries.py   # Tournament queries
│   │   ├── poll_queries.py         # Poll queries
│   │   ├── lake_queries.py         # Lake/ramp queries
│   │   ├── member_queries.py       # Member queries
│   │   ├── user_queries.py         # User queries
│   │   └── data_queries.py         # Data/statistics queries
│   │
│   ├── helpers/                    # Utility modules
│   │   ├── __init__.py
│   │   ├── auth.py                 # Authentication helpers
│   │   ├── crud.py                 # Generic CRUD operations
│   │   ├── forms.py                # Form handling utilities
│   │   ├── response.py             # HTTP response helpers
│   │   ├── sanitize.py             # Input sanitization
│   │   ├── timezone.py             # Timezone utilities (Central Time)
│   │   ├── password_validator.py   # Password validation
│   │   ├── tournament_points.py    # Points calculation logic
│   │   └── logging/                # Logging configuration
│   │
│   ├── email/                      # Email service
│   │   ├── __init__.py
│   │   ├── service.py              # SMTP email sending
│   │   └── templates/              # Email templates
│   │
│   ├── monitoring/                 # Monitoring integration
│   │   ├── __init__.py
│   │   ├── sentry.py               # Sentry configuration
│   │   └── prometheus.py           # Prometheus metrics
│   │
│   ├── csrf_middleware.py          # CSRF protection
│   ├── security_middleware.py      # Security headers
│   └── correlation_middleware.py   # Request correlation IDs
│
├── routes/                         # FastAPI route modules
│   ├── __init__.py
│   │
│   ├── auth/                       # Authentication routes
│   │   ├── __init__.py
│   │   ├── login.py                # Login/logout
│   │   └── register.py             # User registration
│   │
│   ├── pages/                      # Public page routes
│   │   ├── __init__.py
│   │   ├── home.py                 # Homepage
│   │   ├── about.py                # About page
│   │   ├── calendar.py             # Tournament calendar
│   │   ├── bylaws.py               # Club bylaws
│   │   ├── awards.py               # Awards and standings
│   │   ├── roster.py               # Member roster
│   │   ├── profile.py              # User profile
│   │   └── data.py                 # Club data dashboard
│   │
│   ├── voting/                     # Poll and voting routes
│   │   ├── __init__.py
│   │   ├── polls.py                # View polls
│   │   └── vote.py                 # Cast votes
│   │
│   ├── tournaments/                # Tournament routes
│   │   ├── __init__.py
│   │   ├── results.py              # View results
│   │   └── enter_results.py        # Enter tournament results
│   │
│   ├── admin/                      # Admin-only routes
│   │   ├── __init__.py
│   │   ├── core/                   # Admin dashboard and news
│   │   ├── events/                 # Event management
│   │   │   ├── create_event.py     # Event creation
│   │   │   ├── update_event.py     # Event updates
│   │   │   ├── error_handlers.py   # Shared error handling
│   │   │   └── param_builders.py   # Shared parameter builders
│   │   ├── tournaments/            # Tournament management
│   │   ├── polls/                  # Poll creation
│   │   ├── lakes/                  # Lake/ramp management
│   │   └── users/                  # User management
│   │
│   ├── password_reset/             # Password reset flow
│   ├── monitoring/                 # Health and metrics endpoints
│   ├── api/                        # JSON API endpoints
│   └── static/                     # Static file serving
│
├── templates/                      # Jinja2 templates
│   ├── base.html                   # Base layout template
│   ├── macros.html                 # Reusable Jinja2 macros
│   ├── components/                 # Template components
│   │   └── README.md               # Component documentation
│   ├── auth/                       # Authentication templates
│   ├── admin/                      # Admin templates
│   ├── voting/                     # Voting templates
│   ├── tournaments/                # Tournament templates
│   └── email/                      # Email templates
│
├── static/                         # Static assets
│   ├── style.css                   # Custom CSS
│   ├── utils.js                    # Shared JavaScript utilities
│   ├── profile.js                  # Profile page JS
│   ├── roster.js                   # Roster page JS
│   └── enter-results.js            # Results entry JS
│
├── alembic/                        # Database migrations
│   ├── versions/                   # Migration scripts
│   ├── env.py                      # Alembic environment
│   └── script.py.mako              # Migration template
│
├── tests/                          # Test suite
│   ├── conftest.py                 # Shared fixtures
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   ├── routes/                     # Route tests
│   └── security/                   # Security tests
│
├── scripts/                        # Utility scripts
│   ├── setup_db.py                 # Database initialization
│   ├── setup_admin.py              # Admin user creation
│   └── seed_staging_data.py        # Test data seeding
│
├── docs/                           # Documentation
│   ├── ARCHITECTURE.md             # This file
│   ├── TESTING.md                  # Testing guide
│   ├── DATABASE_MIGRATIONS.md      # Migration guide
│   ├── MONITORING.md               # Monitoring setup
│   ├── COMPONENTS.md               # Component reference
│   └── EMAIL_SETUP.md              # Email configuration
│
├── flake.nix                       # Nix development environment
├── docker-compose.prod.yml         # Production Docker config
├── alembic.ini                     # Alembic configuration
├── requirements.txt                # Python dependencies
├── CLAUDE.md                       # AI development guidelines
├── CONTRIBUTING.md                 # Contribution guidelines
├── README.md                       # Project overview
└── SECURITY.md                     # Security policies
```

---

## Core Components

### 1. FastAPI Application (`app.py`)

The application entry point configures:
- Route registration
- Middleware stack (CSRF, security headers, correlation IDs)
- Template engine setup
- Static file serving
- Monitoring integration (Sentry, Prometheus)

```python
# Simplified app structure
from fastapi import FastAPI
from routes import auth, pages, admin, voting, tournaments

app = FastAPI(title="SABC Tournament Management")

# Register middleware
app.add_middleware(CSRFMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Register routes
app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(admin.router, prefix="/admin")
app.include_router(voting.router)
app.include_router(tournaments.router)
```

### 2. Database Layer (`core/db_schema/`)

SQLAlchemy ORM models with type-safe session management:

```python
# Session management pattern
from core.db_schema import get_session, Angler

with get_session() as session:
    anglers = session.query(Angler).filter(Angler.member == True).all()
```

### 3. Query Service (`core/query_service/`)

Centralized, type-safe database queries organized by domain:

```python
from core.query_service import anglers, tournaments, standings

# Get member list
members = anglers.get_active_members()

# Get tournament results
results = tournaments.get_tournament_results(tournament_id=123)

# Calculate AoY standings
aoy = standings.calculate_aoy_standings(year=2024)
```

### 4. Authentication (`core/helpers/auth.py`)

Role-based access control with typed helper functions:

```python
from core.helpers.auth import get_current_user, require_member, require_admin

# Optional auth (public pages)
user = get_current_user(request)

# Required member access
user = require_member(request)  # Raises HTTPException if not member

# Admin-only access
user = require_admin(request)  # Raises HTTPException if not admin
```

### 5. Middleware Stack

Layered security middleware:

1. **CSRF Middleware** - Token generation and validation for POST requests
2. **Security Headers Middleware** - CSP, X-Frame-Options, HSTS
3. **Correlation ID Middleware** - Request tracing across logs

---

## Data Flow

### Request Lifecycle

```
1. HTTP Request
       │
       ▼
2. Middleware (CSRF, Security Headers, Correlation ID)
       │
       ▼
3. Route Handler
       │
       ├── Authentication check (require_auth/require_admin)
       │
       ├── Request validation (Pydantic)
       │
       ├── Business logic (Query Service)
       │
       ├── Database operations (SQLAlchemy ORM)
       │
       └── Response generation
       │
       ▼
4. Template Rendering (Jinja2) or JSON Response
       │
       ▼
5. HTTP Response
```

### Authentication Flow

```
1. User submits login form with email/password
       │
       ▼
2. Password verified against bcrypt hash
       │
       ▼
3. Session created with user ID and role flags
       │
       ▼
4. Secure HTTP-only cookie set
       │
       ▼
5. Subsequent requests include session cookie
       │
       ▼
6. Middleware validates session on each request
```

### Poll Voting Flow

```
1. Admin creates poll with options and time window
       │
       ▼
2. Poll becomes active at start_time
       │
       ▼
3. Members view poll and select option
       │
       ▼
4. Vote recorded in poll_votes table (one vote per member)
       │
       ▼
5. Poll closes at end_time
       │
       ▼
6. Results calculated (winner determined)
       │
       ▼
7. For tournament polls: Tournament auto-created with winning lake/ramp
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Anglers   │───────│   Results   │───────│ Tournaments │
│             │       │             │       │             │
│ id          │       │ id          │       │ id          │
│ name        │       │ angler_id   │       │ event_id    │
│ email       │       │ tournament_ │       │ lake_id     │
│ member      │       │   id        │       │ ramp_id     │
│ is_admin    │       │ total_weight│       │ complete    │
│ phone       │       │ points      │       │ is_team     │
│ year_joined │       │ place       │       └──────┬──────┘
└──────┬──────┘       │ big_bass    │              │
       │              └─────────────┘              │
       │                                           │
       │         ┌─────────────┐           ┌──────┴──────┐
       │         │   Events    │───────────│    Lakes    │
       │         │             │           │             │
       │         │ id          │           │ id          │
       │         │ date        │           │ name        │
       │         │ name        │           │ location    │
       │         │ event_type  │           └──────┬──────┘
       │         │ year        │                  │
       │         └─────────────┘           ┌──────┴──────┐
       │                                   │    Ramps    │
       │                                   │             │
       │         ┌─────────────┐           │ id          │
       └─────────│   Polls     │           │ lake_id     │
                 │             │           │ name        │
                 │ id          │           │ coordinates │
                 │ event_id    │           └─────────────┘
                 │ title       │
                 │ poll_type   │
                 │ starts_at   │       ┌─────────────┐
                 │ closes_at   │───────│ Poll_Options│
                 └──────┬──────┘       │             │
                        │              │ id          │
                        │              │ poll_id     │
                 ┌──────┴──────┐       │ option_text │
                 │ Poll_Votes  │       │ option_data │
                 │             │       └─────────────┘
                 │ id          │
                 │ poll_id     │
                 │ option_id   │
                 │ angler_id   │
                 └─────────────┘
```

### Key Relationships

| Relationship | Type | Description |
|-------------|------|-------------|
| Angler → Results | One-to-Many | Each angler has many tournament results |
| Tournament → Results | One-to-Many | Each tournament has many results |
| Event → Tournament | One-to-One | Each event has one tournament |
| Lake → Ramps | One-to-Many | Each lake has multiple ramps |
| Lake → Tournaments | One-to-Many | Each lake hosts many tournaments |
| Poll → Options | One-to-Many | Each poll has multiple options |
| Poll → Votes | One-to-Many | Each poll receives many votes |
| Angler → Votes | One-to-Many | Members can vote in multiple polls |

---

## Design Decisions

### 1. Server-Side Rendering with HTMX

**Decision**: Use Jinja2 templates with HTMX instead of a JavaScript SPA.

**Rationale**:
- Simpler architecture (no separate frontend build)
- Better SEO out of the box
- Faster initial page loads
- Progressive enhancement (works without JS)
- Type safety extends to templates
- Easier to maintain for small teams

### 2. Type Safety Throughout

**Decision**: Comprehensive type annotations with MyPy enforcement.

**Rationale**:
- Catches bugs at development time
- Better IDE support and autocomplete
- Self-documenting code
- Easier refactoring
- Required for all contributions

### 3. Centralized Query Service

**Decision**: Organize database queries in `core/query_service/` rather than in routes.

**Rationale**:
- Reusable queries across routes
- Easier to optimize and test
- Separation of concerns
- Consistent query patterns

### 4. Session-Based Authentication

**Decision**: Use secure HTTP-only cookies for sessions instead of JWT.

**Rationale**:
- Simpler implementation
- Server-side session revocation
- No token refresh complexity
- Better security for browser clients
- Fits the server-rendered architecture

### 5. Single Interface Design

**Decision**: Inline admin controls instead of separate admin interface.

**Rationale**:
- Consistent user experience
- No context switching
- Fewer templates to maintain
- Admin sees what users see
- Easier permission checking

### 6. PostgreSQL-First

**Decision**: Use PostgreSQL with business logic in the database where appropriate.

**Rationale**:
- Strong data integrity
- Efficient aggregations and views
- ACID compliance
- Excellent performance
- Rich feature set (JSON, arrays, etc.)

---

## Performance Considerations

### Response Time Targets

| Operation | Target | Actual |
|-----------|--------|--------|
| Page load | < 200ms | ~150ms |
| Database query | < 50ms | ~20ms |
| API response | < 100ms | ~80ms |
| Static assets | < 50ms | ~30ms |

### Optimization Strategies

1. **Database Indexes**: Proper indexing on frequently queried columns
2. **Query Optimization**: Efficient JOINs and avoiding N+1 queries
3. **Template Caching**: Jinja2 compiled templates
4. **Static Assets**: CDN for Bootstrap, Chart.js
5. **Connection Pooling**: SQLAlchemy connection pool
6. **Lazy Loading**: Load related data only when needed

### Monitoring

- **Prometheus Metrics**: Request latency, database query times
- **Sentry Performance**: Transaction traces, slow request identification
- **Health Endpoint**: `/health` for uptime monitoring

---

## Security Architecture

See [SECURITY.md](../SECURITY.md) for comprehensive security documentation.

### Key Security Measures

1. **Authentication**: bcrypt password hashing, secure sessions
2. **Authorization**: Role-based access control (Member/Admin)
3. **CSRF Protection**: Token-based protection on all forms
4. **XSS Prevention**: Jinja2 auto-escaping, CSP headers
5. **SQL Injection**: Parameterized queries via SQLAlchemy
6. **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options

---

## Deployment Architecture

### Production Setup

```
                    Internet
                        │
                        ▼
              ┌─────────────────┐
              │   Cloudflare    │  (Optional CDN/DDoS protection)
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     Nginx       │  Port 80/443
              │  (Reverse Proxy)│  SSL Termination
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    FastAPI      │  Port 8000
              │   Application   │  Uvicorn ASGI
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   PostgreSQL    │  Port 5432
              │    Database     │  Persistent Storage
              └─────────────────┘
```

### Docker Compose Services

```yaml
services:
  web:        # FastAPI application
  db:         # PostgreSQL database
  nginx:      # Reverse proxy
  certbot:    # SSL certificate management
```

---

## Related Documentation

- [README.md](../README.md) - Project overview and quick start
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guidelines
- [TESTING.md](TESTING.md) - Test suite documentation
- [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md) - Alembic migration guide
- [MONITORING.md](MONITORING.md) - Monitoring and observability
- [COMPONENTS.md](COMPONENTS.md) - Component reference
- [SECURITY.md](../SECURITY.md) - Security policies

---

**Last Updated**: 2026-02-16
