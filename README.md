# South Austin Bass Club (SABC) Tournament Management System

A modern, minimal tournament management system for the South Austin Bass Club, built with FastAPI for maximum performance and ease of maintenance.

## 🎣 Overview

SABC Tournament Management System is a complete rewrite from Django to FastAPI, focusing on minimal complexity while providing all essential tournament management features:

- **Tournament Scheduling & Results** - Manage monthly tournaments with automated scoring
- **Member Voting System** - Democratic lake selection with tournament location polls
- **Awards & Standings** - Real-time Angler of the Year (AoY) calculations
- **Member Management** - Roster, profiles, and authentication
- **News & Updates** - Club announcements and information

## ✨ Key Features

### For Members
- 🗳️ **Vote on tournament locations** - Democratic lake and ramp selection
- 📊 **View live standings** - Real-time AoY points and rankings
- 📅 **Tournament calendar** - Schedule and event information
- 👤 **Member profiles** - Personal information and tournament history
- 📰 **Club news** - Important announcements and updates

### For Administrators
- 🏆 **Tournament management** - Create events, enter results, manage scoring
- 📊 **Poll creation** - Set up voting for locations and club decisions
- 👥 **Member management** - Add/edit members, manage permissions
- 📈 **Results entry** - Tournament results with automated point calculations
- 🏅 **Awards tracking** - Big bass, tournament wins, season standings

## 🚀 Quick Start

### Prerequisites

- **Nix** (recommended) - For complete development environment
- **Python 3.11+** - If not using Nix
- **SQLite** - Database (no additional setup required)

### Development Setup

#### Option 1: Using Nix (Recommended)

```bash
# Clone the repository
git clone <repository-url>
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
# Clone and enter directory
git clone <repository-url>
cd SABC

# Install dependencies
pip install -r requirements.txt

# Initialize database
python database.py

# Create admin user
python bootstrap_admin.py

# Start server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at [http://localhost:8000](http://localhost:8000)

## 🛠️ Development Commands

### Using Nix (Recommended)

```bash
nix develop                    # Enter development environment

# Core commands
start-app                      # Start FastAPI development server
setup-db                       # Initialize database with schema
reset-db                       # Reset database (delete and recreate)

# Testing
run-tests                      # Run complete test suite
test-backend                   # Backend tests only
test-frontend                  # Frontend tests only
test-integration               # Integration tests
test-quick                     # Quick test subset
test-coverage                  # Generate coverage report
clean-tests                    # Clean test artifacts

# Code quality
format-code                    # Auto-format Python code with ruff
check-code                     # Run linting and type checking
deploy-app                     # Run all checks for deployment
```

### Manual Commands

```bash
# Database
python database.py             # Initialize database
python bootstrap_admin.py      # Create admin user

# Development
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Testing
python tests/run_tests.py      # Run test suite

# Code quality
ruff format .                  # Format code
ruff check .                   # Lint code
```

## 🏗️ Architecture

### Technology Stack
- **FastAPI** - Modern Python web framework
- **SQLite** - Lightweight database (single file)
- **SQLAlchemy Core** - Database access (not ORM for simplicity)
- **Jinja2** - Template engine with conditional admin controls
- **HTMX** - Dynamic UI without JavaScript complexity
- **Nix** - Reproducible development environment

### Design Principles
- **Minimal Complexity** - Absolute minimum code to meet requirements
- **Single Interface** - No separate admin pages, all controls inline
- **Database Calculations** - Push all math to SQL views, not Python
- **Members-Only Voting** - Only `member=true` users can vote
- **Admin-Only Critical Functions** - Results entry, poll creation, member management

### File Structure
```
sabc/
├── app.py              # Single FastAPI application (~3500 lines)
├── database.py         # SQLAlchemy setup + views
├── bootstrap_admin.py  # Admin user creation script
├── tests/              # Test suite
│   ├── run_tests.py    # Test suite runner
├── templates/          # Jinja2 templates
│   ├── base.html       # Base template with navigation
│   ├── index.html      # Home page
│   └── *.html          # Feature templates
├── static/             # CSS and assets
│   └── style.css       # Single stylesheet
├── tests/              # Test suite
├── data/               # Lake/ramp configuration (YAML)
├── flake.nix           # Nix development environment
└── docs/               # Documentation
```

## 📊 Database Schema

### Core Tables
- **anglers** - Members, guests, and admins
- **events** - Tournament dates and federal holidays  
- **tournaments** - Tournament details linked to events
- **results** - Individual tournament results
- **team_results** - Team tournament results (post-2021)
- **polls** - Voting system for locations and decisions
- **poll_options** - Poll choices with JSON data
- **poll_votes** - Member votes (members only)
- **news** - Club announcements

### Business Rules
- **Entry Fee**: $25 ($16 pot, $4 big bass, $3 club, $2 charity)
- **Scoring**: 100 points for 1st, 99 for 2nd, etc.
- **Dead Fish Penalty**: 0.25 lbs per dead fish
- **Fish Limit**: 5 per person (3 in summer months)
- **Big Bass Minimum**: 5 lbs to qualify for payout
- **Team Format**: All tournaments since 2021
- **Voting Period**: 5-7 days before monthly meeting

## 🗳️ Poll System

The system supports multiple poll types:

### Tournament Location Polls
```json
{
  "lake_id": 1,
  "ramp_id": "lake_key_0", 
  "start_time": "06:00",
  "end_time": "15:00"
}
```

### Generic Polls
- **Yes/No questions** - Simple binary choices
- **Multiple choice** - Various options
- **Officer elections** - Candidate selection

## 🧪 Testing

### Running Tests
```bash
# Complete test suite
run-tests

# Specific test types
test-backend                   # API and business logic
test-frontend                  # UI and user interactions  
test-integration               # End-to-end workflows

# Test options
run-tests --filter "poll"      # Filter by name
test-coverage                  # Generate coverage report
```

### Test Coverage
- **Backend Tests**: API endpoints, business logic, database operations
- **Frontend Tests**: UI interactions, form submissions, navigation
- **Integration Tests**: Complete user workflows
- **Security Tests**: Input validation, authentication, authorization

## 🚀 Deployment

### Production Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy Checklist
1. **Environment Variables**: Set production `SECRET_KEY`
2. **Database**: Ensure `sabc.db` exists and is populated
3. **SSL Certificate**: Configure HTTPS (recommended)
4. **Process Manager**: Use systemd, supervisor, or Docker
5. **Reverse Proxy**: Nginx or Apache configuration
6. **Backups**: Automated SQLite file backups

### Environment Variables
```bash
SECRET_KEY=your-production-secret-key
DATABASE_URL=sqlite:///sabc.db  # Optional, defaults to sabc.db
```

## 👥 User Roles

### Members
- Vote in polls (lake selection, club decisions)
- View tournament results and standings
- Access member roster and profiles
- Participate in tournaments

### Guests  
- View public information (calendar, news)
- Cannot vote in polls
- Limited access to member features

### Administrators
- All member privileges plus:
- Create and manage tournaments
- Enter tournament results
- Create polls and manage voting
- Member management and permissions
- News and content management

## 📖 API Documentation

Once the application is running, visit:
- **Interactive API docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI specification**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## 🤝 Contributing

### Development Workflow
1. **Fork and clone** the repository
2. **Enter development environment**: `nix develop`
3. **Set up database**: `setup-db`
4. **Make changes** and test: `run-tests`
5. **Format code**: `format-code`
6. **Submit pull request**

### Code Standards
- **Minimal complexity** - Keep it simple
- **Inline admin controls** - No separate admin interface
- **Database calculations** - Use SQL views for math
- **Test coverage** - Maintain existing test coverage
- **Security first** - Never expose sensitive data

### Before Submitting
- [ ] Tests pass: `run-tests`
- [ ] Code formatted: `format-code`  
- [ ] Linting clean: `check-code`
- [ ] Documentation updated if needed

## 🔒 Security

### Authentication & Authorization
- **Session-based authentication** - Secure cookie sessions
- **Password hashing** - bcrypt with proper salting
- **Role-based access** - Member/admin permissions
- **CSRF protection** - Built-in FastAPI protection

### Data Protection
- **SQL injection prevention** - Parameterized queries
- **XSS prevention** - Template escaping
- **Input validation** - Comprehensive data validation
- **Secure headers** - Security middleware

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 About SABC

The South Austin Bass Club is a community-driven fishing club focused on competitive bass fishing tournaments, member education, and conservation efforts in the Austin, Texas area.

---

**🎣 Tight Lines!** 

For questions, issues, or contributions, please open an issue or contact the development team.