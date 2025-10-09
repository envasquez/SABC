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

## 🚨 SECURITY NOTICE

**CRITICAL**: Read [SECURITY.md](SECURITY.md) before deploying to production.

**Action Required for Existing Deployments:**
- Gmail SMTP password exposed in audit - revoke and regenerate immediately
- Rotate SECRET_KEY for all environments
- Review database credentials and rotate if compromised
- Follow complete credential rotation procedures in [SECURITY.md](SECURITY.md)

**For New Deployments:**
- Never commit `.env` files (already gitignored)
- Use [.env.example](.env.example) template with secure random values
- Store production secrets in platform environment variables (Digital Ocean, AWS, etc.)
- Enable pre-commit hooks to prevent future secret leaks

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
├── tests/                  # Test suite (185 tests)
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── security/           # Security tests
├── scripts/                # Database and admin scripts
├── flake.nix              # Nix development environment
├── CLAUDE.md              # AI development guidelines
└── DATABASE_MIGRATIONS.md # Migration documentation
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

### User Roles

- **Anonymous** - Public content access only
- **Members** - Voting rights, member areas, tournament participation
- **Admins** - Full management access, critical operations

### Security Features

- **Session-based Authentication** - Secure cookie sessions
- **Password Security** - bcrypt hashing with salts
- **Role-based Authorization** - Granular permission control
- **Input Validation** - Pydantic models for all inputs
- **SQL Injection Protection** - Parameterized queries
- **XSS Prevention** - Template escaping
- **CSRF Protection** - Built-in FastAPI protection

## 🚀 Deployment

### Digital Ocean App Platform

The application is designed for deployment on Digital Ocean's App Platform with:

- **Managed PostgreSQL** - Automatic database provisioning
- **Environment Variables** - Secure configuration management
- **Auto-scaling** - Horizontal scaling based on traffic
- **SSL/HTTPS** - Automatic certificate management
- **Health Checks** - Application monitoring

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/sabc
SECRET_KEY=your-secure-secret-key

# Optional
LOG_LEVEL=INFO
DEBUG=false
PORT=8000
```

### Deployment Checklist

- [ ] Environment variables configured
- [ ] Database schema initialized
- [ ] Admin user created
- [ ] Health check endpoint responding
- [ ] SSL certificate configured
- [ ] Domain pointing to application

## 🧪 Testing

### Test Categories

- **Unit Tests** - Core business logic validation
- **Integration Tests** - Database operations and workflows
- **Route Tests** - HTTP endpoint functionality
- **Authentication Tests** - Security and permission validation
- **Poll System Tests** - Voting workflow validation

### Running Tests

```bash
# Complete test suite
nix develop -c run-tests

# Specific test categories
nix develop -c test-backend      # Backend only
nix develop -c test-frontend     # Frontend only
nix develop -c test-integration  # Integration tests
nix develop -c test-coverage     # With coverage report
```

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
