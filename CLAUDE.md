# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
South Austin Bass Club tournament management system - complete rewrite from Django to FastAPI for minimal complexity and maximum performance.

## Key Constraints & Philosophy
- **MINIMAL COMPLEXITY** - Absolute minimum code to meet requirements
- **DATABASE CALCULATIONS** - Push all math to SQL views, not Python
- **MEMBERS ONLY VOTING** - Only `member=true` can vote (never anonymous)
- **ADMIN-ONLY CRITICAL FUNCTIONS** - Results entry, poll creation, member management

## CRITICAL: Reference Site Synchronization Requirements
**MANDATORY VALIDATION**: All database changes MUST be validated against the authoritative reference site at http://167.71.20.3

**CRITICAL**: The reference site is on PORT 80, NOT PORT 443. Always use http://167.71.20.3 (port 80) when accessing the reference site.

### Validation Requirements:
1. **All membership data** must exactly match reference site (names, emails, member/guest status)
2. **Tournament results** must match reference tournaments by date and participants
3. **AoY standings** must match reference site calculations within 1 point
4. **NO placeholder names** - all names must be real people from reference site
5. **NO Guest Angler entries** - convert to actual names or remove

### Validation Workflow:
```bash
# Required before any database changes
python validate_against_reference.py
# Only proceed if validation passes

# After any changes, re-validate
python validate_against_reference.py
# Rollback changes if validation fails
```

**If validation fails, STOP and fix discrepancies before proceeding.**

## CRITICAL RULES

### NEVER USE WILDCARD IMPORTS
**NEVER use wildcard imports like `from module import *`.** Always explicitly import what you need. This makes code clearer, avoids namespace pollution, and helps with debugging.

```python
# ❌ NEVER DO THIS
from fastapi import *
from fastapi.responses import *

# ✅ DO THIS INSTEAD
from fastapi import FastAPI, Request, Form, Query, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, Response
```

### NEVER CONDITIONALLY IMPORT MODULES
**NEVER EVER EVER EVER conditionally import things.** All dependencies that are needed for testing must be properly installed in the environment. Do not use try/except blocks around imports. If something needs to be tested, the environment must be set up properly to support it.

```python
# ❌ NEVER DO THIS
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# ✅ DO THIS INSTEAD
from playwright.sync_api import sync_playwright
```

## Development Commands
```bash
# Enter development environment (Nix required)
nix develop

# Core development commands (in Nix shell)
start-app        # Run FastAPI development server
setup-db         # Initialize database with schema
reset-db         # Reset database (delete and recreate)

# Testing commands (in Nix shell)
run-tests        # Run complete test suite
test-backend     # Run backend tests only
test-frontend    # Run frontend tests only
test-integration # Run integration tests
test-quick       # Run quick test subset
test-coverage    # Generate coverage report
clean-tests      # Clean test artifacts

# Code quality commands (in Nix shell)
format-code      # Auto-format Python code with ruff
check-code       # Run linting and type checking
deploy-app       # Run all checks for deployment

# Manual commands (if not using Nix)
python database.py              # Initialize database
python bootstrap_admin.py       # Create admin user
python tests/run_tests.py       # Run test suite
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## File Structure
```
sabc/
├── app.py              # Single FastAPI application
├── database.py         # SQLAlchemy setup + views
├── models.py           # Table definitions (if separate from database.py)
├── routes/             # Route modules (if modularized)
├── templates/          # Jinja2 templates with conditional admin controls
│   ├── base.html       # Base template with navigation
│   ├── index.html      # Home page
│   └── login.html      # Authentication
├── static/             # Single CSS file
│   └── style.css       # All custom styles
├── bootstrap_admin.py  # Admin user creation script
├── test_basic.py       # Basic tests
└── docs/               # Documentation
```

## Navigation Structure
Main navigation links (available to all users):
- **Home** (/)
- **About** (/about) - Club information and history
- **Bylaws** (/bylaws) - Club rules and regulations
- **Calendar** (/calendar) - Tournament schedule and events
- **Awards** (/awards) - Annual awards and standings

Authenticated user links:
- **Polls** (/polls) - Active voting for members
- **Members** (/members) - Member roster and profiles

Admin dropdown menu additions:
- New Tournament creation
- New Poll creation
- Admin dashboard

## Database Design Principles
- **SQLite only** - Single file, zero config
- **Minimal foreign keys** - Only where absolutely necessary
- **JSON for flexibility** - Poll option_data, not separate tables
- **SQL views for calculations** - Points, standings, awards all in database

## Core Database Tables
```sql
-- Essential tables only
anglers (id, name, email, member, is_admin)
events (id, date, year, description)
lakes (id, name, location)
ramps (id, lake_id, name, coordinates)
polls (id, title, poll_type, starts_at, closes_at, winning_option_id)
poll_options (id, poll_id, option_text, option_data JSON)
poll_votes (id, poll_id, option_id, angler_id)
tournaments (id, event_id, poll_id, lake_id, entry_fee, fish_limit, is_paper, complete)
results (id, tournament_id, angler_id, num_fish, total_weight, big_bass_weight, dead_fish_penalty, disqualified, buy_in)
team_results (id, tournament_id, angler1_id, angler2_id, total_weight)
```

## SABC Bylaws Requirements
- **Entry fee**: $25 ($16 pot, $4 big bass, $3 club, $2 charity)
- **Scoring**: 100 points for 1st, 99 for 2nd, etc.
- **Dead fish penalty**: 0.25 lbs per dead fish
- **Fish limit**: 5 per person (3 in summer)
- **Big bass minimum**: 5 lbs to qualify
- **Team tournaments**: All tournaments are team format (since 2021)
- **Voting schedule**: 5-7 days before monthly meeting
- **Member dues**: $25/year renewable January

## UI/UX Rules
- **Inline admin controls**: `{% if user.is_admin %}` around admin buttons
- **HTMX modals**: Edit forms as overlays, not new pages
- **Contextual editing**: Edit buttons next to content they modify
- **Single interface**: Same pages for all users, admins see extra controls

## Technology Stack
- **FastAPI** - Web framework
- **SQLite** - Database (single file)
- **SQLAlchemy Core** - Database access (not ORM)
- **Jinja2** - Templates with conditional rendering
- **HTMX** - Inline editing without JavaScript complexity
- **Nix** - Development environment

## Authentication & Authorization
- **Simple email/password** - No OAuth
- **FastAPI sessions** - Cookie-based
- **Admin bootstrap** - Command line script for first admin
- **Password reset** - Basic email-based recovery

## Poll System Logic
```python
# Poll types with different option_data structures
tournament_location: {"lake_id": 1, "ramp_id": 3, "start_time": "06:00", "end_time": "15:00"}
yes_no: {} # Simple text options
multiple_choice: {} # Simple text options
officer_election: {} # Simple text options
```

## Event Lifecycle
1. **Admin creates event** (date only) → Auto-creates tournament location poll
2. **Poll opens** → Members vote on lake/ramp/times
3. **Poll closes** → Winning option displayed
4. **Admin creates tournament** → Uses poll results
5. **Tournament held** → Admin enters results
6. **Tournament complete** → Display standings

## Display Logic
```python
if event.date > today:
    if poll.is_active():
        show_voting_interface()
    elif poll.is_closed():
        show_poll_results()
else:  # Past event
    if tournament.complete:
        show_tournament_results()
```

## Data Migration Strategy
- **Export Django**: `python manage.py dumpdata users tournaments polls > data.json`
- **Import to SQLite**: Python scripts to parse JSON and insert
- **Password reset**: Users reset passwords (security best practice)
- **Validate**: Compare record counts and key data points


## Scoring Calculations (SQL Views)
```sql
-- Points: 100 for 1st, 99 for 2nd, etc.
-- Zero fish: 2 points less than last place with fish
-- Buy-ins: 4 points less than last place with fish
-- Disqualified: 0 points
```

## Key Business Rules
- **Members only vote**: `WHERE a.member = true`
- **Big bass carryover**: If no 5+ lb fish, pot carries to next tournament
- **Paper tournaments**: Fish measured vs weighed
- **Buy-in deadline**: Friday after tournament (manual tracking)
- **Dead fish penalty**: Subtracted from total weight

## Error Handling Philosophy
- **Fail gracefully** - Show user-friendly messages
- **Log everything** - For debugging
- **Validate early** - Check permissions and data before processing
- **Manual admin fixes** - For complex disputes

## Performance Requirements
- **Load time**: < 200ms
- **Single file backup**: SQLite database
- **Memory usage**: < 50MB
- **Lines of code**: < 1000 total

## Testing Strategy
- **Real data testing** - Use migrated Django data
- **Admin workflow testing** - Poll creation → Tournament → Results
- **Member voting testing** - Ensure only members can vote
- **Edge case testing** - Ties, empty polls, cancellations

## Deployment
- **Digital Ocean droplet** - Keep current hosting
- **Simple deployment**: `git pull && restart service`
- **Daily backups**: Automated SQLite file backup
- **SSL/Domain**: Use existing setup

## Common Patterns

### Admin-Only Route Protection
```python
@app.get("/admin/polls/create")
async def create_poll(user: User = Depends(require_admin)):
    # Admin-only functionality
```

### Conditional Template Rendering
```html
<!-- Tournament results table -->
<tr>
    <td>{{ angler.name }}</td>
    <td>{{ result.total_weight }}</td>
    {% if user.is_admin %}
        <td>
            <button hx-get="/results/{{ result.id }}/edit">Edit</button>
            <button hx-delete="/results/{{ result.id }}">Delete</button>
        </td>
    {% endif %}
</tr>
```

### Poll Option Data Structure
```python
# Tournament location poll
option_data = {
    "lake_id": 1,
    "ramp_id": 3,
    "start_time": "06:00",
    "end_time": "15:00"
}

# Simple polls (yes/no, multiple choice)
option_data = {}  # Just use option_text
```

## What NOT to Build
- **Separate admin interface** - Everything inline
- **Complex user roles** - Just member/admin
- **Automated enforcement** - Manual admin processes
- **Real-time features** - Keep it simple
- **Mobile app** - Responsive web only
- **Advanced reporting** - Basic views sufficient

## Poll Visualization System
**Enhanced in December 2024** - Comprehensive overhaul of poll results display with professional data visualization.

### Generic Polls
- **Vertical Bar Charts**: Replaced simple progress bars with gradient vertical bars
- **Vote Counts Inside Bars**: White text displays vote counts within colored bars for better visibility
- **Zero-Vote Filtering**: Options with no votes are automatically hidden from display
- **Consistent Styling**: Professional color scheme with hover effects and smooth animations

### Tournament Location Polls
- **Interactive Lake/Ramp Charts**: Two-level visualization showing lakes and ramp breakdowns
- **Smart Display Logic**: Auto-shows ramp breakdown when only one lake has votes
- **Complete Data Validation**: Ensures all options have proper lake_id, ramp_id, start_time, end_time
- **Consistent Vote Display**: Vote counts inside bars matching generic poll styling

### UI/UX Improvements
- **Unified Design Language**: Consistent styling across all poll types
- **Removed Redundant Banners**: Eliminated duplicate participation statistics
- **Description Formatting**: Honor line breaks in poll descriptions with `white-space: pre-line`
- **Responsive Layout**: Aligned column widths between poll types for visual consistency

### Development Tools
- **Data Validation**: Complete lake/ramp/time combinations from YAML configuration
- **Edge Case Testing**: Proper handling of single votes and various vote distributions

## Success Criteria
✅ Faster than Django (< 200ms load times)
✅ Easier to maintain (< 1000 lines of code)
✅ All bylaws requirements met
✅ All admin functions inline
✅ Members can vote, admins can manage
✅ Historical data migrated successfully
✅ Professional poll visualization system