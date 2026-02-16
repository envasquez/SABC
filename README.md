# South Austin Bass Club (SABC) Tournament Management System

A modern, type-safe tournament management system built with FastAPI and PostgreSQL, designed for simplicity, performance, and maintainability.

## 🎣 Overview

SABC Tournament Management System provides comprehensive tournament management for the South Austin Bass Club with a focus on minimal complexity and maximum performance:

- **Tournament Management** - Schedule events, enter results, automated scoring
- **Democratic Voting** - Member polls for tournament locations and club decisions
- **Awards & Standings** - Real-time Angler of the Year (AoY) calculations
- **Member Management** - Secure authentication, roles, and profiles
- **Club Information** - News, bylaws, calendar, and member roster

## ✨ Key Features

### 🗳️ **Member Voting System**
- Democratic lake and ramp selection for tournaments
- Poll creation with multiple question types
- Member-only voting with secure authentication
- Automatic tournament creation from winning poll results

### 🏆 **Tournament Management**
- Complete tournament lifecycle management
- Automated point calculations and standings
- Team tournament support (post-2021 format)
- Big bass tracking with carryover functionality

### 📊 **Real-time Standings**
- Live Angler of the Year (AoY) points tracking
- Historical tournament results and statistics
- Awards tracking and season summaries
- Performance analytics and trends

### 👥 **Member Portal**
- Secure member authentication and profiles
- Role-based access (Member/Admin)
- Member roster and contact information
- Personal tournament history

### 📰 **Club Information Hub**
- Club news and announcements
- Tournament calendar and schedules
- Club bylaws and regulations
- Historical information and archives

## 🔒 Security Best Practices

**Before deploying to production**, review [SECURITY.md](SECURITY.md) for comprehensive security guidance.

**Essential Security Practices:**
- Never commit `.env` files (already gitignored)
- Use [.env.example](.env.example) template with secure random values
- Store production secrets in platform environment variables (Digital Ocean, AWS, etc.)
- Enable pre-commit hooks to prevent secret leaks
- Rotate credentials regularly (quarterly recommended)
- Use strong SECRET_KEY values (64+ random characters)

---

## 🚀 Quick Start

### Prerequisites

- **Nix** (recommended) - Complete development environment
- **Python 3.11+** - If not using Nix
- **PostgreSQL 17+** - Database system

### Development Setup

#### Option 1: Using Nix (Recommended)

```bash
# Clone the repository
git clone https://github.com/envasquez/SABC.git
cd SABC

# Enter development environment (includes PostgreSQL)
nix develop

# Initialize database
setup-db

# Start development server
start-app
```

#### Option 2: Manual Setup

```bash
# Clone repository
git clone https://github.com/envasquez/SABC.git
cd SABC

# Install Python dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
createdb sabc
export DATABASE_URL="postgresql://username:password@localhost:5432/sabc"

# Initialize database schema
python scripts/setup_db.py

# Create admin user
python scripts/setup_admin.py

# Start server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at [http://localhost:8000](http://localhost:8000)

## 🛠️ Development Commands

### Core Commands (Nix Environment)

```bash
nix develop                    # Enter development environment

# Database management
setup-db                       # Initialize PostgreSQL database
reset-db                       # Reset database (destructive)

# Development server
start-app                      # Start FastAPI server (localhost:8000)

# Code quality (mandatory before commits)
format-code                    # Auto-format with ruff
check-code                     # Type checking + linting
deploy-app                     # Full deployment validation

# Testing
run-tests                      # Complete test suite
test-backend                   # Backend tests only
test-frontend                  # Frontend tests only
test-coverage                  # Coverage report
```

### Manual Commands

```bash
# Database
python scripts/setup_db.py
python scripts/setup_admin.py

# Development
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Code quality
ruff format .                  # Format code
ruff check .                   # Lint code
mypy .                         # Type checking
```

## 🏗️ Architecture

### Technology Stack

- **Backend**: FastAPI 0.115+ with Python 3.11+
- **Database**: PostgreSQL 17+ with SQLAlchemy ORM + Alembic migrations
- **Frontend**: Jinja2 templates + HTMX for interactivity
- **Type Safety**: Comprehensive type annotations throughout
- **Monitoring**: Sentry (errors) + Prometheus (metrics)
- **Development**: Nix for reproducible environment
- **Deployment**: Digital Ocean App Platform

### Design Principles

- **Type Safety First** - Complete type annotations with MyPy validation
- **Minimal Complexity** - Simplest solution that meets requirements
- **Database-Driven** - Business logic in SQL views and functions
- **Single Interface** - Inline admin controls, no separate admin app
- **Performance-Focused** - Sub-200ms response times

### Project Structure

```
sabc/
├── app.py                     # FastAPI application entry point
├── core/                      # Core business logic
│   ├── database.py           # Database connection and queries
│   ├── schemas.py            # Pydantic models for validation
│   ├── deps.py               # Dependency injection
│   ├── db_schema/            # Database schema and models
│   ├── query_service/        # Centralized query service
│   ├── monitoring/           # Sentry + Prometheus monitoring
│   └── helpers/              # Utility modules
│       ├── auth.py           # Authentication helpers
│       ├── timezone.py       # Timezone utilities (Central Time)
│       └── logging.py        # Logging configuration
├── routes/                  # FastAPI route modules
│   ├── auth/               # Authentication routes
│   ├── pages/              # Public pages
│   ├── voting/             # Member voting
│   ├── tournaments/        # Tournament results
│   ├── monitoring/         # Metrics endpoint
│   └── admin/              # Admin-only routes
│       ├── core/           # Admin dashboard and news
│       ├── events/         # Event management
│       ├── polls/          # Poll creation and management
│       ├── tournaments/    # Tournament management
│       ├── lakes/          # Lake and ramp management
│       └── users/          # User management
├── alembic/                # Database migrations (Alembic)
│   ├── versions/           # Migration scripts
│   └── env.py              # Migration environment
├── templates/              # Jinja2 templates
├── static/                 # CSS and assets
├── tests/                  # Test suite (909 tests)
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── routes/             # Route/HTTP endpoint tests
│   └── security/           # Security tests
├── scripts/                # Database and admin scripts
├── flake.nix              # Nix development environment
├── CLAUDE.md              # AI development guidelines
└── docs/                  # Documentation files
```

## 📊 Database Schema

### Core Entities

```sql
-- User management
anglers (id, name, email, member, is_admin, phone, year_joined)

-- Tournament system
events (id, date, name, event_type, year, description)
tournaments (id, event_id, lake_id, ramp_id, complete, is_team)
results (id, tournament_id, angler_id, total_weight, points)
team_results (id, tournament_id, angler1_id, angler2_id, total_weight)

-- Voting system
polls (id, event_id, title, poll_type, starts_at, closes_at)
poll_options (id, poll_id, option_text, option_data)
poll_votes (id, poll_id, option_id, angler_id)

-- Location data
lakes (id, name, location)
ramps (id, lake_id, name, coordinates)

-- Content management
news (id, title, content, published, priority, created_at)
```

### Business Rules

- **Entry Fee**: $25 ($16 pot, $4 big bass, $3 club, $2 charity)
- **Scoring**: 100 points for 1st place, 99 for 2nd, etc.
- **Dead Fish Penalty**: 0.25 lbs deduction per dead fish
- **Fish Limits**: 5 fish per person (3 in summer months)
- **Big Bass Minimum**: 5 lbs to qualify for payout
- **Team Format**: All tournaments since 2021
- **Voting Window**: 5-7 days before monthly meeting

## 🗳️ Poll System

### Poll Types

#### Tournament Location Polls
Structured data for tournament parameters:
```json
{
  "lake_id": 1,
  "ramp_id": 3,
  "start_time": "06:00",
  "end_time": "15:00"
}
```

#### Generic Polls
- **Yes/No Questions** - Binary choices
- **Multiple Choice** - Various options
- **Officer Elections** - Candidate selection

### Poll Workflow
1. **Admin creates poll** with options and time window
2. **Members vote** during active period
3. **Poll closes** automatically at deadline
4. **Winning option** determines tournament details
5. **Tournament created** automatically from poll results

## 🔒 Security & Authentication

### Defense-in-Depth Security Architecture

SABC implements a comprehensive, multi-layered security approach to protect member data, prevent unauthorized access, and maintain system integrity. Security is enforced at every layer from network to application to database.

### User Roles & Authorization

- **Anonymous** - Public content access only (tournament results, calendar, club information)
- **Members** - Voting rights, member areas, tournament participation, profile management
- **Admins** - Full management access, critical operations, user management, poll creation

**Authorization Model:**
- Role-based access control (RBAC) enforced at route level
- Granular permissions with helper functions (`require_admin`, `require_member`)
- Session-based authentication with secure cookie handling
- Automatic session expiration and renewal

### Authentication & Session Security

**Password Security:**
- bcrypt hashing with automatic salt generation (cost factor: 12)
- Password validation on registration and login
- Secure password reset flow via email verification
- No plaintext password storage or transmission

**Session Management:**
- Secure HTTP-only cookies prevent XSS session theft
- CSRF tokens on all state-changing operations
- Session expiration and automatic renewal
- Logout invalidates server-side session state

### Input Validation & Data Protection

**Request Validation:**
- Pydantic models validate all input data with strict type checking
- SQLAlchemy ORM with parameterized queries prevents SQL injection
- HTML escaping in Jinja2 templates prevents XSS attacks
- File upload restrictions and validation (if applicable)

**Data Sanitization:**
- All user input sanitized before database insertion
- Template auto-escaping enabled by default
- JSON data validation for poll options and structured data
- Email validation using standard RFC-compliant patterns

### Network & Application Security

**HTTP Security Headers:**
- Content Security Policy (CSP) headers
- X-Frame-Options prevents clickjacking
- X-Content-Type-Options prevents MIME sniffing
- Strict-Transport-Security (HSTS) for HTTPS enforcement

**API Security:**
- Rate limiting on authentication endpoints
- Request size limits to prevent DoS attacks
- CORS configuration for API access control
- Secure error handling (no sensitive data in error messages)

### Automated Security Scanning

**Pre-commit Security Hooks:**

The codebase includes comprehensive automated security checks that run before every commit:

- **Bandit** - Python security linter detecting common vulnerabilities (hardcoded passwords, SQL injection patterns, insecure functions)
- **detect-private-key** - Scans for accidentally committed SSH keys, SSL certificates, and private keys
- **Ruff** - Modern Python linter with security-focused rules
- **MyPy** - Type safety enforcement prevents type-related security bugs
- **check-merge-conflict** - Prevents committing merge conflict markers
- **debug-statements** - Detects leftover debugger imports
- **trailing-whitespace** - Code hygiene and consistency

**Automated Testing:**

- **909 automated tests** (909 passing, 1 skipped) covering:
  - **SQL Injection Protection** - Tests parameterized queries and ORM safety
  - **CSRF Protection** - Validates token generation and verification
  - **XSS Prevention** - Tests template escaping and output sanitization
  - **Authorization Tests** - Verifies role-based access controls
  - **Authentication Tests** - Password hashing, session management, login flows
  - **Input Validation** - Pydantic model validation and edge cases

**Continuous Integration:**
- GitHub Actions runs full test suite on every pull request
- All security tests must pass before merge
- Pre-commit hooks enforce code quality and security standards

### Secret Management Best Practices

**Environment Variables:**
- All secrets stored in environment variables (never in code)
- `.env` files gitignored to prevent accidental commits
- `.env.example` provides template without sensitive data
- Production secrets managed via platform environment (Digital Ocean, AWS)

**Secret Rotation:**
- Regular rotation of `SECRET_KEY` and database credentials
- SMTP password rotation documented in [SECURITY.md](SECURITY.md)
- API keys and tokens managed securely
- Immediate rotation procedures for compromised secrets

**Protected Secrets:**
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Session encryption and CSRF tokens
- `SMTP_PASSWORD` - Email service authentication
- `SENTRY_DSN` - Error monitoring service key

### Security Monitoring & Incident Response

**Real-time Monitoring:**
- Failed login attempts tracked via Prometheus metrics
- Sentry captures security-related errors and exceptions
- Suspicious activity patterns trigger alerts
- Rate limiting prevents brute force attacks

**Audit Logging:**
- Admin actions logged with timestamps and user context
- Database changes tracked via SQLAlchemy events
- Authentication events (login, logout, failed attempts) recorded
- Critical operations require explicit admin authorization

For detailed monitoring configuration and incident response procedures, see the [🔍 Monitoring & Observability](#-monitoring--observability) section below.

### Security Compliance & Best Practices

**Development Standards:**
- Type-safe codebase prevents entire classes of vulnerabilities
- Code review required for all security-sensitive changes
- Security testing integrated into CI/CD pipeline
- Regular dependency updates and vulnerability scanning

**Deployment Security:**
- HTTPS/TLS encryption for all production traffic
- Firewall configuration restricts unnecessary ports
- Database access limited to application layer
- Regular security audits and penetration testing

**Data Privacy:**
- Minimal data collection (only necessary for functionality)
- Sensitive data filtered before sending to Sentry
- Member contact information restricted to authenticated users
- GDPR-compliant data handling practices

### Security Documentation

For comprehensive security information:
- **[SECURITY.md](SECURITY.md)** - Security policies, vulnerability reporting, credential rotation
- **[docs/MONITORING.md](docs/MONITORING.md)** - Monitoring setup and incident response
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Secure development practices

**Reporting Security Vulnerabilities:**

If you discover a security vulnerability, please follow responsible disclosure:
1. Do NOT open a public GitHub issue
2. Email security details to the maintainers (see [SECURITY.md](SECURITY.md))
3. Allow reasonable time for response and patching
4. Coordinate public disclosure timing

---

## 🔍 Monitoring & Observability

SABC implements comprehensive monitoring and observability to ensure system reliability, detect issues proactively, and maintain optimal performance. The monitoring stack provides real-time insights into application health, user behavior, and security incidents.

### Monitoring Stack Overview

**Dual-layer Monitoring:**
- **Sentry** - Error tracking, exception monitoring, and performance profiling
- **Prometheus** - Metrics collection, time-series data, and application instrumentation

**Benefits:**
- Proactive issue detection before users report problems
- Performance degradation alerts and trend analysis
- Security incident detection (failed logins, anomalies)
- Data-driven decision making for optimization
- Historical analysis and capacity planning

### Sentry Error Tracking

**Automatic Error Capture:**
- All unhandled exceptions automatically reported to Sentry
- Full stack traces with local variable context
- HTTP request context (method, URL, headers, user agent)
- User context (authenticated user ID and email)
- Environment and release tracking for deployment correlation

**Privacy-First Configuration:**
- Sensitive data automatically filtered before transmission
- HTTP headers filtered: `authorization`, `cookie`, `x-csrf-token`
- Environment variables filtered: `DATABASE_URL`, `SECRET_KEY`, `SMTP_PASSWORD`
- Query strings and form data excluded (may contain tokens/passwords)
- PII scrubbing for email addresses and personal data

**Performance Monitoring:**
- Transaction traces for slow requests (10% sampling in production)
- Database query performance tracking via SQLAlchemy integration
- HTTP request duration and throughput metrics
- Bottleneck identification and optimization opportunities

**Configuration:**
```bash
# Enable Sentry by setting DSN environment variable
SENTRY_DSN=https://your-key@sentry.io/your-project-id

# Optional: Track deployments and releases
RELEASE_VERSION=v1.2.3
ENVIRONMENT=production
```

**Sampling Strategy:**
- Production: 10% of transactions (reduces overhead and costs)
- Development/Test: 0% (no performance data collected)
- Errors: 100% capture rate (all errors reported)

### Prometheus Metrics

**HTTP Request Metrics:**
- `http_requests_total{method, endpoint, status}` - Total request count by method, endpoint, and status code
- `http_request_duration_seconds{method, endpoint}` - Request latency histogram (0.01s to 10s buckets)

**Database Metrics:**
- `db_query_duration_seconds{query_type}` - Database query latency histogram
- `db_connections_active` - Current active database connections

**Application Metrics:**
- `active_sessions` - Number of active user sessions
- `poll_votes_total{poll_type}` - Total poll votes by poll type
- `failed_logins_total` - Total failed login attempts (security monitoring)
- `email_sent_total{email_type, status}` - Email delivery tracking

**Metrics Endpoint:**
```
GET /metrics
```

Returns metrics in Prometheus text format for scraping. **IMPORTANT**: Restrict access via firewall in production to prevent unauthorized metric access.

**Grafana Dashboards:**

Example queries for monitoring dashboards:
- Request rate: `rate(http_requests_total[5m])`
- Request latency (p95): `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- Error rate: `rate(http_requests_total{status=~"5.."}[5m])`
- Failed login rate: `rate(failed_logins_total[5m])`

### Security Monitoring Integration

**Failed Login Tracking:**
- `failed_logins_total` metric increments on authentication failures
- Alert on rate > 50/minute (potential brute force attack)
- Grafana dashboards visualize attack patterns
- Sentry captures detailed error context for investigation

**Anomaly Detection:**
- Unusual traffic patterns detected via request rate metrics
- Database connection pool exhaustion alerts
- Slow query detection via `db_query_duration_seconds`
- Email delivery failure monitoring

**Incident Response Workflow:**
1. Alert triggered via Prometheus/Grafana or Sentry
2. Review metrics and error context in monitoring dashboards
3. Investigate logs and database state
4. Deploy fixes and monitor recovery
5. Post-incident review and documentation

### Performance Monitoring

**Real-time Performance Tracking:**
- Sub-200ms target for page load times
- Database query optimization via latency metrics
- Slow transaction identification in Sentry
- Resource utilization tracking

**Alerting Thresholds:**
- Request error rate > 5%
- Request latency p95 > 1 second
- Database query latency p95 > 100ms
- Active database connections > 80% of pool size
- Failed login rate > 50/minute

**Performance Impact:**
- Sentry: ~1-2ms overhead per request (10% sampling)
- Prometheus: < 1ms per request
- Total monitoring overhead: < 3ms per request

### Monitoring Best Practices

**Daily Operations:**
1. Review Sentry dashboard for new or recurring errors
2. Check Grafana dashboards for performance degradation
3. Monitor alert notifications (email/Slack)
4. Analyze slow queries and optimize as needed
5. Track user activity metrics (poll votes, logins)

**Deployment Tracking:**
- Set `RELEASE_VERSION` environment variable for each deployment
- Sentry tracks errors by release for regression detection
- Compare metrics before and after deployment
- Monitor error rates during rollout

**Documentation:**
For detailed monitoring setup, Prometheus configuration, and Grafana dashboard creation, see [docs/MONITORING.md](docs/MONITORING.md).

---

## 🚀 Deployment

### Production: Docker Compose on Digital Ocean Droplet

**Current production deployment** uses Docker Compose with:

- **Docker Containers** - Web (FastAPI), PostgreSQL, Nginx, Certbot
- **Manual Deployment** - SSH → git pull → [restart.sh](restart.sh)
- **SSL** - Let's Encrypt via Certbot
- **Cost** - ~$12/month (Basic Droplet + included bandwidth)

**Deployment:**
```bash
ssh root@<production-ip>
cd /opt/sabc
./restart.sh  # Pulls latest code, rebuilds containers, restarts
```

See [docker-compose.prod.yml](docker-compose.prod.yml) for full configuration.

### Staging: Same Docker Setup on Separate Droplet

For safe testing before production deployment:

- **Infrastructure** - Separate droplet mirroring production
- **Configuration** - [STAGING_DEPLOYMENT.md](docs/STAGING_DEPLOYMENT.md)
- **Test Data** - Automated seeding with [scripts/seed_staging_data.py](scripts/seed_staging_data.py)
- **Cost** - ~$6/month (smaller droplet)

### Alternative: Digital Ocean App Platform (PaaS)

For a managed platform approach, see [STAGING_ENVIRONMENT.md](docs/STAGING_ENVIRONMENT.md).

Benefits:
- Managed PostgreSQL, auto-scaling, automatic SSL
- Higher cost (~$18-30/month vs $6-12/month for Droplet)

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/sabc
SECRET_KEY=your-secure-secret-key
DB_PASSWORD=your-db-password

# SMTP
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@saustinbc.com

# Optional
LOG_LEVEL=INFO
DEBUG=false
WEBSITE_URL=https://saustinbc.com
SENTRY_DSN=https://xxx@sentry.io/yyy
ENVIRONMENT=production
```

### Deployment Checklist

- [ ] Environment variables configured in `.env`
- [ ] Database container healthy
- [ ] Admin user created via [scripts/setup_admin.py](scripts/setup_admin.py)
- [ ] Health check endpoint responding (`/health`)
- [ ] SSL certificate configured (Certbot)
- [ ] Domain DNS pointing to droplet
- [ ] Nginx reverse proxy running
- [ ] Firewall configured (UFW: 22, 80, 443)

## 🧪 Testing

SABC maintains a comprehensive automated test suite ensuring code quality, security, and reliability. All tests run automatically via CI/CD and pre-commit hooks.

### Test Suite Status

**Current Test Coverage:**
- **909 passing tests**
- **1 skipped test** (rate limiting test, production-only)
- **78%+ coverage** overall, >90% for critical paths

### Test Categories

**Unit Tests** - Core Business Logic
- Helper functions and utilities
- Authentication and authorization logic
- Data validation and transformation
- Timezone and date handling
- Profile security and data sanitization

**Integration Tests** - Database & Service Testing
- SQLAlchemy ORM operations
- Database queries and transactions
- Service layer interactions
- Email sending and notifications
- Poll creation and voting workflows

**Route Tests** - HTTP Endpoint Testing
- FastAPI route functionality
- Request/response validation
- Template rendering
- HTMX interactions
- Redirect and error handling

**Security Tests** - Vulnerability Prevention
- **CSRF Protection** - Token generation, validation, and enforcement on state-changing operations
- **SQL Injection** - Parameterized query testing, ORM safety validation
- **XSS Prevention** - Template escaping, output sanitization, HTML injection protection
- **Authorization** - Role-based access control, permission enforcement, session validation
- **Authentication** - Password hashing, login flows, session management, failed login handling

### Testing Tools & Frameworks

**Core Testing Stack:**
- **pytest** - Primary test framework with fixtures and parametrization
- **FastAPI TestClient** - HTTP endpoint testing with full request/response cycle
- **SQLite** - In-memory test database for fast, isolated tests
- **PostgreSQL** - Production database (tests use SQLite for speed)

**Test Utilities:**
- Fixture factories for test data generation
- Mock services for external dependencies (email, Sentry)
- Custom assertions for common validation patterns
- Test database setup and teardown automation

### Coverage Targets

**Critical Path Coverage (>90%):**
- Authentication and authorization flows
- Poll creation, voting, and result calculation
- Tournament result entry and point calculations
- Admin operations and data management
- Security-sensitive operations

**Overall Coverage:**
- Unit tests: >95% coverage
- Integration tests: >85% coverage
- Route tests: >80% coverage
- Combined: >90% for critical business logic

### Running Tests

```bash
# Complete test suite
nix develop -c run-tests

# Specific test categories
nix develop -c test-backend      # Backend only
nix develop -c test-frontend     # Frontend only
nix develop -c test-integration  # Integration tests
nix develop -c test-coverage     # With coverage report

# Manual test execution
pytest                           # All tests
pytest tests/unit                # Unit tests only
pytest tests/security            # Security tests only
pytest -v                        # Verbose output
pytest --cov=core --cov-report=html  # Coverage report
```

### CI/CD Integration

**GitHub Actions Workflow:**
- Runs on every pull request and push to main
- Executes full test suite (909 tests)
- Generates coverage reports
- Fails build on test failures or coverage drops
- Automatically runs code quality checks (Ruff, MyPy, Bandit)

**Pre-commit Testing Hooks:**
- Type checking (MyPy) before commit
- Security scanning (Bandit) before commit
- Code linting (Ruff) with auto-fix
- Fast unit test subset (optional hook)

### Test Development Guidelines

**Writing New Tests:**
1. Add test cases for all new features and bug fixes
2. Follow existing test patterns and fixtures
3. Use descriptive test names (`test_admin_can_create_poll`)
4. Test both success and failure scenarios
5. Include edge cases and boundary conditions

**Security Test Requirements:**
- Test authorization for all protected endpoints
- Validate input sanitization and escaping
- Verify CSRF token enforcement
- Test SQL injection resistance
- Confirm XSS prevention measures

**Test Isolation:**
- Each test runs in isolated database transaction
- No dependencies between tests
- Cleanup handled automatically via fixtures
- Deterministic test execution order

### Performance Testing

**Load Testing:**
- Verify sub-200ms response time targets
- Test concurrent user scenarios
- Database connection pool stress testing
- Memory usage profiling

**Regression Prevention:**
- Baseline performance metrics tracked
- CI/CD monitors response time degradation
- Slow test identification and optimization

For detailed testing guidelines and best practices, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📈 Performance

### Performance Targets

- **Page Load Time**: < 200ms average
- **Database Queries**: Optimized with proper indexing
- **Memory Usage**: < 100MB per instance
- **Response Time**: 95th percentile < 500ms

### Optimization Strategies

- **Database Views** - Pre-computed aggregations
- **Query Optimization** - Efficient joins and indexes
- **Template Caching** - Jinja2 template compilation
- **Static Asset Optimization** - Minimal CSS/JS footprint

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development guidelines.

### Quick Start for Contributors

1. **Fork and clone** the repository
2. **Setup environment**: `nix develop`
3. **Initialize database**: `setup-db`
4. **Make changes** following code standards
5. **Quality checks**: `format-code && check-code`
6. **Test changes**: `run-tests`
7. **Submit pull request**

### Code Quality Requirements

- ✅ **Type Safety**: Zero MyPy errors
- ✅ **Code Style**: Ruff formatting and linting
- ✅ **Test Coverage**: >90% for critical paths
- ✅ **Documentation**: Updated for changes
- ✅ **Performance**: No regression in response times

## 📖 API Documentation

Interactive API documentation available when running:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Spec**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 About SABC

The South Austin Bass Club is a community-driven fishing club focused on competitive bass fishing tournaments, member education, and conservation efforts in the Austin, Texas area.

### Club History

Founded to promote bass fishing excellence and camaraderie among Austin-area anglers, SABC has been organizing monthly tournaments and fostering fishing education for years. The club emphasizes fair competition, conservation, and community building through shared fishing experiences.

---

**🎣 Tight Lines!**

For questions, issues, or contributions, please [open an issue](https://github.com/envasquez/SABC/issues) or contact the development team.

*Built with ❤️ for the South Austin Bass Club community*
