# SABC Component Architecture Guide

## Overview

This document provides a comprehensive guide to the SABC component architecture, covering frontend templates, JavaScript utilities, and backend helpers. The goal is to maintain a clean, maintainable codebase by promoting component reuse and avoiding duplication.

## Table of Contents

1. [Design Principles](#design-principles)
2. [Frontend Components](#frontend-components)
   - [Jinja2 Macros](#jinja2-macros)
   - [JavaScript Utilities](#javascript-utilities)
   - [JavaScript Classes](#javascript-classes)
3. [Backend Components](#backend-components)
   - [Core Helpers](#core-helpers)
   - [CRUD Operations](#crud-operations)
4. [Integration Patterns](#integration-patterns)
5. [Best Practices](#best-practices)
6. [Anti-Patterns](#anti-patterns)

---

## Design Principles

### 1. Single Responsibility
Each component should do one thing well. Avoid "Swiss Army knife" functions that try to handle too many use cases.

### 2. Reusability
Components should be designed for reuse across multiple contexts. Use parameters and callbacks to make them flexible.

### 3. Type Safety
All Python code must have proper type annotations. JavaScript should use JSDoc comments for documentation.

### 4. Documentation First
Write documentation before implementing. If you can't explain it clearly, redesign it.

### 5. Test Everything
Components should have test coverage. Critical components need comprehensive tests.

---

## Frontend Components

### Jinja2 Macros

All Jinja2 macros are defined in [`templates/macros.html`](../templates/macros.html). For detailed usage examples, see [`templates/components/README.md`](../templates/components/README.md).

#### Security Components
- **`csrf_token(request)`** - CSRF protection for forms
  - **When to use**: Every POST form without exception
  - **Example**: `{{ csrf_token(request) }}`

#### UI Components
- **`alert(type, message, dismissible=True)`** - Bootstrap alerts
  - **When to use**: Displaying success/error/warning messages
  - **Example**: `{{ alert('success', 'Saved successfully!') }}`

- **`badge(text, color='primary', icon='')`** - Generic badges
  - **When to use**: Status indicators, labels, counts
  - **Example**: `{{ badge('Active', 'success', 'check-circle') }}`

- **`officer_badge(position)`** - Officer position badges
  - **When to use**: Displaying officer roles
  - **Example**: `{{ officer_badge('President') }}`

- **`member_badge(is_member)`** - Member status indicators
  - **When to use**: Showing membership status
  - **Example**: `{{ member_badge(angler.member) }}`

#### Form Components
- **`form_field(label, name, type='text', ...)`** - Form input fields
  - **When to use**: Creating consistent form inputs
  - **Example**: `{{ form_field('Email', 'email', type='email', required=True) }}`

- **`time_select_options(start_hour=5, ...)`** - Time dropdown options
  - **When to use**: Tournament start/end time selectors
  - **Example**: `{{ time_select_options(start_hour=6, end_hour=10) }}`
  - **Impact**: Saved 120+ lines in polls.html

#### Container Components
- **`card(title='', header_class='bg-primary text-white', ...)`** - Bootstrap cards
  - **When to use**: Grouping related content
  - **Example**:
    ```jinja2
    {% call card(title='Results') %}
      <p>Content here</p>
    {% endcall %}
    ```

- **`modal(id, title, size='')`** - Bootstrap modals
  - **When to use**: Dialog boxes, confirmations
  - **Example**:
    ```jinja2
    {% call modal('detailsModal', 'Details', size='modal-lg') %}
      <p>Modal content</p>
    {% endcall %}
    ```

- **`delete_modal(modal_id, title, message, ...)`** - Delete confirmation modals
  - **When to use**: Confirming destructive actions
  - **Example**: `{{ delete_modal('deleteUserModal', 'Delete User', '...', ...) }}`

#### Display Components
- **`stat_card(icon, title, value, color='primary')`** - Statistics cards
  - **When to use**: Dashboard statistics, metrics
  - **Example**: `{{ stat_card('trophy', 'Tournaments', 24, 'success') }}`

- **`seasonal_history_card(seasonal_history)`** - Tournament history
  - **When to use**: Displaying seasonal tournament statistics
  - **Example**: `{{ seasonal_history_card(seasonal_history) }}`
  - **Impact**: Saved 130+ lines across multiple templates

---

### JavaScript Utilities

All JavaScript utilities are defined in [`static/utils.js`](../static/utils.js).

#### Browser Compatibility
```javascript
// Auto-runs on page load
checkBrowserCompatibility() // Returns boolean, shows warning if incompatible
```
- **Purpose**: Detect unsupported browsers and show warning
- **Features detected**: fetch, Promise, arrow functions, classList, localStorage
- **Action**: Automatically displays warning banner for incompatible browsers

#### Security Utilities
```javascript
escapeHtml(text) // XSS prevention
getCsrfToken()   // Extract CSRF token from cookies
```

**`escapeHtml(text)`**
- **Purpose**: Prevent XSS attacks by escaping HTML special characters
- **When to use**: Before inserting user-generated content into DOM
- **Example**:
  ```javascript
  const username = escapeHtml(userInput);
  element.innerHTML = `<p>Welcome, ${username}</p>`;
  ```

**`getCsrfToken()`**
- **Purpose**: Extract CSRF token for AJAX requests
- **When to use**: Making state-changing requests (POST, PUT, DELETE)
- **Example**:
  ```javascript
  const token = getCsrfToken();
  fetch('/api/endpoint', {
      headers: { 'x-csrf-token': token }
  });
  ```

#### User Feedback
```javascript
showToast(message, type='info', duration=5000)
```
- **Purpose**: Display non-blocking toast notifications
- **Types**: 'success', 'error', 'warning', 'info'
- **When to use**: AJAX operation feedback, non-critical notifications
- **Example**:
  ```javascript
  showToast('Saved successfully', 'success');
  showToast('Operation failed', 'error', 3000);
  ```

#### HTTP Utilities
```javascript
fetchWithRetry(url, options={}, retries=3)
deleteRequest(url, retries=3)
handleApiError(response, defaultMessage)
```

**`fetchWithRetry(url, options, retries)`**
- **Purpose**: Fetch with automatic retry on server errors
- **Behavior**:
  - Retries on 5xx errors (server issues)
  - Does NOT retry on 4xx errors (client issues)
  - Exponential backoff: 1s, 2s, 4s
- **When to use**: API requests that may fail due to temporary server issues
- **Example**:
  ```javascript
  const response = await fetchWithRetry('/api/data');
  if (response.ok) {
      const data = await response.json();
  }
  ```

**`deleteRequest(url, retries)`**
- **Purpose**: Convenience function for DELETE requests with CSRF and retry
- **When to use**: Deleting resources via AJAX
- **Example**:
  ```javascript
  const response = await deleteRequest('/admin/users/123');
  if (response.ok) {
      showToast('Deleted successfully', 'success');
  }
  ```

**`handleApiError(response, defaultMessage)`**
- **Purpose**: Consistent error handling and user feedback
- **Behavior**: Displays error message via toast, throws Error
- **When to use**: After fetch requests to handle failures
- **Example**:
  ```javascript
  const response = await fetch('/api/endpoint');
  await handleApiError(response, 'Failed to load data');
  ```

#### Modal Utilities
```javascript
showModal(modalId)
hideModal(modalId)
```
- **Purpose**: Programmatic modal control
- **When to use**: Showing/hiding modals from JavaScript
- **Example**:
  ```javascript
  showModal('confirmationModal');
  hideModal('confirmationModal');
  ```

---

### JavaScript Classes

#### LakeRampSelector

**Purpose**: Reusable component for lake/ramp dropdown selection

**Use Cases**:
1. **Admin event creation** (API-based)
2. **Poll creation** (pre-loaded data)
3. **Any form** with lake/ramp selection

**Constructor Options**:
```javascript
{
    lakeSelectId: string,        // ID of lake select element
    rampSelectId: string,        // ID of ramp select element
    lakesData: Array|Object,     // Lakes data (varies by use case)
    useApi: boolean,             // Fetch ramps via API?
    emptyText: string            // Default: '-- Select Ramp --'
}
```

**Methods**:
- `loadRampsForLake(lakeName)` - Load by lake name (API pattern)
- `loadRampsForLakeId(lakeId)` - Load by lake ID (pre-loaded pattern)
- `setRampValue(rampValue)` - Set selected ramp
- `autoWire(useId=false)` - Auto-wire lake change event

**Example 1: API-based (Admin Events)**
```javascript
const selector = new LakeRampSelector({
    lakeSelectId: 'lake_select',
    rampSelectId: 'ramp_select',
    lakesData: lakesData,  // [{key: 'travis', name: 'Lake Travis'}, ...]
    useApi: true
});
selector.autoWire();  // Auto-load ramps when lake changes
```

**Example 2: Pre-loaded (Polls)**
```javascript
const selector = new LakeRampSelector({
    lakeSelectId: 'poll_lake',
    rampSelectId: 'poll_ramp',
    lakesData: lakesAndRamps,  // {1: {name: 'Lake Travis', ramps: [...]}, ...}
    useApi: false
});
selector.autoWire(true);  // Use lake ID instead of name
```

---

#### DeleteConfirmationManager

**Purpose**: Reusable component for delete confirmation workflows

**Pattern**: Show modal → Require "DELETE" confirmation → Execute delete

**Constructor Options**:
```javascript
{
    modalId: string,                 // ID of modal element
    itemNameElementId: string,       // ID for displaying item name
    confirmInputId: string,          // ID of confirmation input
    confirmButtonId: string,         // ID of confirm button
    deleteUrlTemplate: Function,     // (id) => delete URL
    onSuccess: Function,             // Callback after success
    onError: Function,               // Callback after error
    confirmText: string              // Default: 'DELETE'
}
```

**Methods**:
- `confirm(itemId, itemName)` - Show confirmation modal

**Example: User Deletion**
```javascript
const deleteManager = new DeleteConfirmationManager({
    modalId: 'deleteUserModal',
    itemNameElementId: 'deleteUserName',
    confirmInputId: 'deleteConfirmInput',
    confirmButtonId: 'confirmDeleteBtn',
    deleteUrlTemplate: (id) => `/admin/users/${id}`,
    onSuccess: () => location.reload(),
    onError: (error) => showToast(`Failed: ${error}`, 'error')
});

// Trigger confirmation
deleteManager.confirm(123, 'John Doe');
```

**HTML Requirements**:
```html
<div class="modal" id="deleteUserModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5>Delete User</h5>
            </div>
            <div class="modal-body">
                <p>Type <strong>DELETE</strong> to confirm deletion of:</p>
                <p><strong id="deleteUserName"></strong></p>
                <input type="text" id="deleteConfirmInput" class="form-control">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-danger" id="confirmDeleteBtn" disabled>Delete</button>
            </div>
        </div>
    </div>
</div>
```

**Impact**: Saved 269 lines across 6 templates in Phase 2 refactoring

---

## Backend Components

### Core Helpers

All backend helpers are in [`core/helpers/`](../core/helpers/).

#### Authentication (`core/helpers/auth.py`)

**Key Functions**:
```python
def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from session (None if not authenticated)"""

def require_auth(request: Request) -> Dict[str, Any]:
    """Require authenticated user (raises HTTPException if not)"""

def require_member(request: Request) -> Dict[str, Any]:
    """Require verified member (raises HTTPException if not)"""

def require_admin(request: Request) -> Dict[str, Any]:
    """Require admin user (raises HTTPException if not)"""

def is_admin(request: Request) -> bool:
    """Check if current user is admin (returns boolean)"""
```

**Usage Pattern**:
```python
from core.helpers.auth import require_admin, get_current_user

@router.get("/admin/dashboard")
async def admin_dashboard(request: Request):
    user = require_admin(request)  # Raises 403 if not admin
    # Admin logic here
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user
    })

@router.get("/profile")
async def profile(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login")
    # Profile logic here
```

**When to use**:
- `get_current_user()` - When authentication is optional
- `require_auth()` - When authentication is required
- `require_member()` - When verified membership is required (polls, voting)
- `require_admin()` - When admin privileges are required
- `is_admin()` - When you need boolean check without exception

---

#### Response Helpers (`core/helpers/response.py`)

**Key Functions**:
```python
def error_redirect(path: str, message: str, status_code: int = 303) -> RedirectResponse:
    """Redirect with error message"""

def success_redirect(path: str, message: str, status_code: int = 303) -> RedirectResponse:
    """Redirect with success message"""

def json_error(message: str, status_code: int = 400) -> JSONResponse:
    """Return JSON error response"""

def json_success(
    data: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    status_code: int = 200
) -> JSONResponse:
    """Return JSON success response"""

def sanitize_error_message(error: Exception, generic_message: str) -> str:
    """Sanitize error for user display (logs full error)"""

def get_client_ip(request: Request) -> str:
    """Extract client IP address"""

def set_user_session(request: Request, user_id: int) -> None:
    """Set user session (prevents session fixation)"""
```

**Usage Pattern**:
```python
from core.helpers.response import error_redirect, success_redirect

@router.post("/admin/events")
async def create_event(request: Request, ...):
    try:
        # Create event logic
        return success_redirect("/admin/events", "Event created successfully")
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        return error_redirect("/admin/events/new", "Failed to create event")
```

**When to use**:
- `error_redirect()` / `success_redirect()` - After form submissions (POST-Redirect-GET pattern)
- `json_error()` / `json_success()` - For AJAX/API endpoints
- `sanitize_error_message()` - Before showing errors to users (prevents information disclosure)

---

#### Form Helpers (`core/helpers/forms.py`)

**Key Functions**:
```python
def get_form_data(request: Request) -> Dict[str, Any]:
    """Extract form data from request"""

def validate_required_fields(
    data: Dict[str, Any],
    required: List[str]
) -> Optional[str]:
    """Check if required fields are present (returns error message or None)"""

def clean_phone_number(phone: str) -> str:
    """Normalize phone number format"""
```

**Usage Pattern**:
```python
from core.helpers.forms import get_form_data, validate_required_fields

@router.post("/admin/users")
async def create_user(request: Request):
    data = await get_form_data(request)

    error = validate_required_fields(data, ['name', 'email'])
    if error:
        return error_redirect("/admin/users/new", error)

    # Create user logic
```

---

#### Sanitization (`core/helpers/sanitize.py`)

**Key Functions**:
```python
def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Sanitize user input text"""

def sanitize_email(email: str) -> str:
    """Validate and normalize email address"""

def sanitize_url(url: str) -> str:
    """Validate and sanitize URLs"""
```

**When to use**: Before storing or displaying user-generated content

---

#### Password Validation (`core/helpers/password_validator.py`)

**Key Functions**:
```python
def validate_password(password: str) -> Tuple[bool, List[str]]:
    """Validate password strength (returns valid, errors)"""

def hash_password(password: str) -> str:
    """Hash password with bcrypt"""

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
```

**Requirements**:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

**Usage Pattern**:
```python
from core.helpers.password_validator import validate_password, hash_password

valid, errors = validate_password(password)
if not valid:
    return error_redirect("/register", " ".join(errors))

hashed = hash_password(password)
# Store hashed password
```

---

#### Tournament Points (`core/helpers/tournament_points.py`)

**Key Functions**:
```python
def calculate_tournament_points(
    results: List[Result],
    point_system: str = 'standard'
) -> List[Dict[str, Any]]:
    """Calculate tournament points based on placement"""
```

**Point Systems**:
- `standard` - 100 for 1st, 99 for 2nd, etc.
- Other systems can be added

---

#### Timezone (`core/helpers/timezone.py`)

**Key Functions**:
```python
def to_local_time(dt: datetime, timezone: str = 'US/Central') -> datetime:
    """Convert UTC to local timezone"""

def to_utc_time(dt: datetime, timezone: str = 'US/Central') -> datetime:
    """Convert local timezone to UTC"""

def format_datetime(dt: datetime, format: str = '%Y-%m-%d %H:%M') -> str:
    """Format datetime for display"""
```

**Usage Pattern**:
```python
from core.helpers.timezone import to_local_time, format_datetime

# Convert UTC from database to local for display
event_time_local = to_local_time(event.date)
formatted = format_datetime(event_time_local, '%B %d, %Y at %I:%M %p')
```

---

### CRUD Operations

The [`core/helpers/crud.py`](../core/helpers/crud.py) module provides generic CRUD helpers introduced in Phase 4 refactoring.

#### delete_entity()

**Purpose**: Generic DELETE endpoint handler with validation and cascade hooks

**Function Signature**:
```python
def delete_entity(
    request: Request,
    entity_id: int,
    model_class: Type[T],
    redirect_url: Optional[str] = None,
    success_message: str = "Item deleted successfully",
    error_message: str = "Failed to delete item",
    validation_check: Optional[Callable[[Session, int], Optional[str]]] = None,
    pre_delete_hook: Optional[Callable[[Session, int], None]] = None,
    self_delete_check: Optional[Callable[[Dict[str, Any], int], bool]] = None,
) -> Response:
```

**Parameters**:
- `request` - FastAPI request (for auth)
- `entity_id` - ID of entity to delete
- `model_class` - SQLAlchemy model class (e.g., `User`, `Event`)
- `redirect_url` - If provided, returns RedirectResponse; if None, returns JSONResponse
- `success_message` - Success message for user
- `error_message` - Error message prefix
- `validation_check` - Optional callback for FK validation (return error string or None)
- `pre_delete_hook` - Optional callback for cascade deletes
- `self_delete_check` - Optional callback to prevent self-deletion

**Return Behavior**:
- If `redirect_url` provided → Returns `RedirectResponse` (for form submissions)
- If `redirect_url` is None → Returns `JSONResponse` (for AJAX requests)

**Example 1: Simple Delete (User)**
```python
from core.helpers.crud import delete_entity
from core.db_schema import Angler

def _check_self_delete(user: Dict[str, Any], user_id: int) -> bool:
    """Check if user is trying to delete themselves."""
    return user.get("id") == user_id

@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int) -> Response:
    """Delete a user account (cannot delete yourself)."""
    return delete_entity(
        request, user_id, Angler,
        success_message="User deleted successfully",
        error_message="Failed to delete user",
        self_delete_check=_check_self_delete,
    )
```

**Example 2: Delete with FK Validation (Ramp)**
```python
from core.helpers.crud import delete_entity, check_foreign_key_usage
from core.db_schema import Ramp, Tournament

def _check_ramp_usage(session: Session, ramp_id: int) -> Optional[str]:
    """Check if ramp is referenced by tournaments."""
    return check_foreign_key_usage(
        session, Tournament, Tournament.ramp_id, ramp_id,
        "Cannot delete ramp that is referenced by tournaments",
    )

@router.delete("/admin/ramps/{ramp_id}")
async def delete_ramp(request: Request, ramp_id: int) -> Response:
    """Delete a ramp (cannot delete if referenced by tournaments)."""
    return delete_entity(
        request, ramp_id, Ramp,
        success_message="Ramp deleted successfully",
        error_message="Failed to delete ramp",
        validation_check=_check_ramp_usage,
    )
```

**Example 3: Delete with Cascade (Poll)**
```python
from core.helpers.crud import delete_entity, bulk_delete
from core.db_schema import Poll, PollVote, PollOption

def _delete_poll_cascade(session: Session, poll_id: int) -> None:
    """Delete poll votes and options before deleting poll."""
    bulk_delete(session, PollVote, [PollVote.poll_id == poll_id])
    bulk_delete(session, PollOption, [PollOption.poll_id == poll_id])

@router.delete("/admin/polls/{poll_id}")
async def delete_poll(request: Request, poll_id: int) -> Response:
    """Delete a poll and all associated votes and options."""
    return delete_entity(
        request, poll_id, Poll,
        success_message="Poll deleted successfully",
        error_message="Failed to delete poll",
        pre_delete_hook=_delete_poll_cascade,
    )
```

**Example 4: Both POST and DELETE Methods (News)**
```python
@router.post("/admin/news/{news_id}/delete")
async def delete_news_post(request: Request, news_id: int) -> Response:
    """POST endpoint for deleting news (for form submissions)."""
    return delete_entity(
        request, news_id, News,
        redirect_url="/admin/news",  # Causes redirect
        success_message="News deleted successfully",
        error_message="Failed to delete news",
    )

@router.delete("/admin/news/{news_id}")
async def delete_news(request: Request, news_id: int) -> Response:
    """DELETE endpoint for deleting news (for AJAX requests)."""
    return delete_entity(
        request, news_id, News,
        # No redirect_url = returns JSON
        success_message="News deleted successfully",
        error_message="Failed to delete news",
    )
```

**Impact**: Phase 4 eliminated ~155 lines of duplicate DELETE logic across 5 route files

---

#### check_foreign_key_usage()

**Purpose**: Check if entity is referenced by foreign keys

**Function Signature**:
```python
def check_foreign_key_usage(
    session: Session,
    target_model: Type[Any],
    foreign_key_field: Any,
    entity_id: int,
    error_message: str,
) -> Optional[str]:
```

**Returns**: Error message string if referenced, None if safe to delete

**Example**:
```python
from core.helpers.crud import check_foreign_key_usage
from core.db_schema import Tournament, Ramp

def _check_ramp_usage(session: Session, ramp_id: int) -> Optional[str]:
    return check_foreign_key_usage(
        session,
        Tournament,              # Model that references the entity
        Tournament.ramp_id,      # FK field
        ramp_id,                 # Entity ID to check
        "Cannot delete ramp that is referenced by tournaments"
    )
```

---

#### bulk_delete()

**Purpose**: Delete multiple records matching conditions

**Function Signature**:
```python
def bulk_delete(
    session: Session,
    model_class: Type[Any],
    conditions: List[Any],
) -> int:
```

**Returns**: Number of records deleted

**Example**:
```python
from core.helpers.crud import bulk_delete
from core.db_schema import PollVote, PollOption

# Delete all votes and options for a poll
bulk_delete(session, PollVote, [PollVote.poll_id == poll_id])
bulk_delete(session, PollOption, [PollOption.poll_id == poll_id])
```

---

## Integration Patterns

### Pattern 1: Form Submission with Validation

**Scenario**: User submits a form to create/update an entity

**Flow**:
1. Extract form data with `get_form_data()`
2. Validate required fields with `validate_required_fields()`
3. Sanitize user input with `sanitize_text()` / `sanitize_email()`
4. Create/update entity in database
5. Redirect with success/error message

**Code**:
```python
from core.helpers.auth import require_admin
from core.helpers.forms import get_form_data, validate_required_fields
from core.helpers.response import error_redirect, success_redirect
from core.helpers.sanitize import sanitize_text, sanitize_email
from core.db_schema import Angler, get_session

@router.post("/admin/users")
async def create_user(request: Request):
    user = require_admin(request)
    data = await get_form_data(request)

    # Validate
    error = validate_required_fields(data, ['name', 'email'])
    if error:
        return error_redirect("/admin/users/new", error)

    # Sanitize
    name = sanitize_text(data['name'], max_length=100)
    email = sanitize_email(data['email'])

    # Create
    try:
        with get_session() as session:
            new_user = Angler(name=name, email=email)
            session.add(new_user)
            session.commit()
        return success_redirect("/admin/users", "User created successfully")
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        return error_redirect("/admin/users/new", "Failed to create user")
```

---

### Pattern 2: AJAX API Endpoint

**Scenario**: Frontend makes AJAX request for data or action

**Flow**:
1. Authenticate with `require_admin()` / `require_member()`
2. Extract/validate request data
3. Perform database operation
4. Return JSON success/error response

**Code**:
```python
from core.helpers.auth import require_admin
from core.helpers.response import json_error, json_success
from core.db_schema import Tournament, get_session

@router.get("/api/tournaments/{tournament_id}")
async def get_tournament(request: Request, tournament_id: int):
    user = require_admin(request)

    try:
        with get_session() as session:
            tournament = session.query(Tournament).filter(
                Tournament.id == tournament_id
            ).first()

            if not tournament:
                return json_error("Tournament not found", status_code=404)

            return json_success(data={
                "id": tournament.id,
                "event_id": tournament.event_id,
                "lake_id": tournament.lake_id,
                "complete": tournament.complete
            })
    except Exception as e:
        logger.error(f"Failed to fetch tournament: {e}")
        return json_error("Failed to fetch tournament", status_code=500)
```

---

### Pattern 3: Page Render with Optional Auth

**Scenario**: Display page that works for both authenticated and anonymous users

**Flow**:
1. Get current user with `get_current_user()` (returns None if not logged in)
2. Fetch data (filter based on user permissions)
3. Render template with user context

**Code**:
```python
from core.helpers.auth import get_current_user
from core.db_schema import Tournament, get_session

@router.get("/tournaments")
async def tournaments_page(request: Request):
    user = get_current_user(request)

    with get_session() as session:
        # Everyone can see completed tournaments
        query = session.query(Tournament).filter(Tournament.complete == True)

        # Only admins see incomplete tournaments
        if not user or not user.get('is_admin'):
            query = query.filter(Tournament.complete == True)

        tournaments = query.all()

    return templates.TemplateResponse("tournaments.html", {
        "request": request,
        "user": user,
        "tournaments": tournaments
    })
```

---

### Pattern 4: DELETE Endpoint (POST + DELETE Methods)

**Scenario**: Support both form submission (POST) and AJAX (DELETE) for deletion

**Flow**:
1. Create two endpoints using `delete_entity()`
2. POST endpoint has `redirect_url` (for forms)
3. DELETE endpoint has no `redirect_url` (returns JSON for AJAX)

**Code**:
```python
from core.helpers.crud import delete_entity
from core.db_schema import News

@router.post("/admin/news/{news_id}/delete")
async def delete_news_post(request: Request, news_id: int) -> Response:
    """Form submission endpoint"""
    return delete_entity(
        request, news_id, News,
        redirect_url="/admin/news",  # Redirects after delete
        success_message="News deleted successfully",
        error_message="Failed to delete news",
    )

@router.delete("/admin/news/{news_id}")
async def delete_news(request: Request, news_id: int) -> Response:
    """AJAX endpoint"""
    return delete_entity(
        request, news_id, News,
        # No redirect_url = returns JSON
        success_message="News deleted successfully",
        error_message="Failed to delete news",
    )
```

---

### Pattern 5: Frontend DELETE with Confirmation

**Scenario**: User clicks delete button, sees confirmation modal, deletion executes

**HTML**:
```html
{% from "macros.html" import delete_modal %}

<!-- Delete button triggers modal -->
<button onclick="confirmDelete({{ news.id }}, '{{ news.title | escape }}')"
        class="btn btn-danger">
    Delete
</button>

<!-- Confirmation modal -->
{{ delete_modal(
    modal_id='deleteNewsModal',
    title='Delete News',
    message='Are you sure you want to delete this news article?',
    form_action='',
    item_name='',
    csrf_token_value=csrf_token
) }}
```

**JavaScript**:
```javascript
const deleteManager = new DeleteConfirmationManager({
    modalId: 'deleteNewsModal',
    itemNameElementId: 'deleteNewsName',
    confirmInputId: 'deleteConfirmInput',
    confirmButtonId: 'confirmDeleteBtn',
    deleteUrlTemplate: (id) => `/admin/news/${id}`,
    onSuccess: () => {
        showToast('News deleted successfully', 'success');
        setTimeout(() => location.reload(), 1000);
    },
    onError: (error) => showToast(`Failed: ${error}`, 'error')
});

function confirmDelete(newsId, newsTitle) {
    deleteManager.confirm(newsId, newsTitle);
}
```

---

## Best Practices

### Frontend Best Practices

#### 1. Always Use CSRF Tokens
```jinja2
<!-- ✅ CORRECT -->
<form method="POST" action="/submit">
    {{ csrf_token(request) }}
    <!-- form fields -->
</form>

<!-- ❌ WRONG - Missing CSRF token -->
<form method="POST" action="/submit">
    <!-- form fields -->
</form>
```

#### 2. Escape User-Generated Content
```javascript
// ✅ CORRECT
const username = escapeHtml(userInput);
element.innerHTML = `<p>${username}</p>`;

// ❌ WRONG - XSS vulnerability
element.innerHTML = `<p>${userInput}</p>`;
```

#### 3. Use Macros for Repeated UI
```jinja2
<!-- ✅ CORRECT - Using macro -->
{% from "macros.html" import form_field %}
{{ form_field('Email', 'email', type='email', required=True) }}

<!-- ❌ WRONG - Manual HTML duplication -->
<div class="mb-3">
    <label for="email" class="form-label">Email</label>
    <input type="email" class="form-control" id="email" name="email" required>
</div>
```

#### 4. Provide User Feedback
```javascript
// ✅ CORRECT - Show feedback
const response = await deleteRequest('/admin/users/123');
if (response.ok) {
    showToast('User deleted successfully', 'success');
} else {
    showToast('Failed to delete user', 'error');
}

// ❌ WRONG - Silent failure
await deleteRequest('/admin/users/123');
```

---

### Backend Best Practices

#### 1. Type Annotations Everywhere
```python
# ✅ CORRECT
from typing import List, Dict, Any

def get_tournaments(event_id: int) -> List[Dict[str, Any]]:
    """Get tournaments for an event."""
    # implementation

# ❌ WRONG - No type hints
def get_tournaments(event_id):
    # implementation
```

#### 2. Use Helper Functions
```python
# ✅ CORRECT
from core.helpers.crud import delete_entity

@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int) -> Response:
    return delete_entity(request, user_id, Angler, ...)

# ❌ WRONG - Duplicate DELETE boilerplate
@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int):
    user = require_admin(request)
    try:
        with get_session() as session:
            # ... 30 lines of boilerplate ...
```

#### 3. Sanitize Error Messages
```python
# ✅ CORRECT
from core.helpers.response import sanitize_error_message

try:
    # operation
except Exception as e:
    error_msg = sanitize_error_message(e, "Operation failed")
    return json_error(error_msg)

# ❌ WRONG - Exposes internal details
except Exception as e:
    return json_error(str(e))  # Might leak database paths, etc.
```

#### 4. Validate User Input
```python
# ✅ CORRECT
from core.helpers.forms import validate_required_fields
from core.helpers.sanitize import sanitize_text

data = await get_form_data(request)
error = validate_required_fields(data, ['name', 'email'])
if error:
    return error_redirect("/form", error)

name = sanitize_text(data['name'], max_length=100)

# ❌ WRONG - Direct database insertion
name = data['name']  # No validation or sanitization
```

---

## Anti-Patterns

### ❌ Don't: Duplicate Code

**Bad**:
```python
# In delete_user.py
@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int):
    user = require_admin(request)
    try:
        with get_session() as session:
            entity = session.query(Angler).filter(Angler.id == user_id).first()
            if entity:
                session.delete(entity)
        return json_success(message="User deleted")
    except Exception as e:
        return json_error("Failed to delete user")

# In delete_event.py - EXACT SAME CODE
@router.delete("/admin/events/{event_id}")
async def delete_event(request: Request, event_id: int):
    user = require_admin(request)
    try:
        with get_session() as session:
            entity = session.query(Event).filter(Event.id == event_id).first()
            if entity:
                session.delete(entity)
        return json_success(message="Event deleted")
    except Exception as e:
        return json_error("Failed to delete event")
```

**Good**: Use `delete_entity()` helper

---

### ❌ Don't: Mix Concerns

**Bad**:
```python
@router.post("/admin/events")
async def create_event(request: Request):
    # Auth
    if 'user_id' not in request.session:
        raise HTTPException(403)
    user = get_user(request.session['user_id'])
    if not user['is_admin']:
        raise HTTPException(403)

    # Form extraction
    form = await request.form()
    data = dict(form)

    # Validation
    if not data.get('name'):
        return error_redirect("/form", "Name required")

    # Sanitization
    name = data['name'].strip()[:100]

    # Business logic
    # ...
```

**Good**: Use helper functions for each concern
```python
@router.post("/admin/events")
async def create_event(request: Request):
    user = require_admin(request)  # Auth
    data = await get_form_data(request)  # Form extraction
    error = validate_required_fields(data, ['name'])  # Validation
    if error:
        return error_redirect("/form", error)
    name = sanitize_text(data['name'], max_length=100)  # Sanitization
    # Business logic
```

---

### ❌ Don't: Skip CSRF Tokens

**Bad**:
```html
<form method="POST" action="/admin/delete">
    <!-- Missing CSRF token! -->
    <button type="submit">Delete</button>
</form>
```

**Good**:
```html
{% from "macros.html" import csrf_token %}
<form method="POST" action="/admin/delete">
    {{ csrf_token(request) }}
    <button type="submit">Delete</button>
</form>
```

---

### ❌ Don't: Return Raw Exceptions to Users

**Bad**:
```python
try:
    # operation
except Exception as e:
    return json_error(str(e))  # Might leak: "could not connect to server: Connection refused Is the server running on host '10.0.1.5' and accepting TCP/IP connections on port 5432?"
```

**Good**:
```python
from core.helpers.response import sanitize_error_message

try:
    # operation
except Exception as e:
    error_msg = sanitize_error_message(e, "Operation failed")
    return json_error(error_msg)  # Returns: "Operation failed"
```

---

### ❌ Don't: Hardcode HTML in JavaScript

**Bad**:
```javascript
function showAlert(message) {
    const html = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    document.body.insertAdjacentHTML('afterbegin', html);
}
```

**Good**: Use `showToast()` utility
```javascript
showToast(message, 'error');
```

---

## Component Lifecycle

### Creating New Components

1. **Identify Duplication**: Find 3+ instances of similar code
2. **Design Interface**: Define clear parameters and behavior
3. **Document First**: Write usage examples before implementing
4. **Implement**: Create the component with type hints/JSDoc
5. **Test**: Write tests or manually verify all use cases
6. **Refactor**: Replace duplicated code with component
7. **Update Docs**: Add to this guide and component README

### Modifying Existing Components

1. **Check Usage**: Find all places component is used (grep/search)
2. **Design Change**: Ensure backward compatibility or plan migration
3. **Update Implementation**: Make changes with type safety
4. **Test All Usage**: Verify all existing uses still work
5. **Update Documentation**: Reflect changes in docs

### Deprecating Components

1. **Mark Deprecated**: Add deprecation notice in docstring
2. **Provide Alternative**: Document replacement component
3. **Migrate Gradually**: Update usage over time
4. **Remove After Grace Period**: Delete after all migration complete

---

## Metrics & Impact

### Refactoring Progress (Phases 1-4)

| Component Type | Lines Saved | Files Modified |
|----------------|-------------|----------------|
| Template Macros | 345 | 11 |
| JavaScript Classes | 269 | 7 |
| Backend CRUD | 155 | 6 |
| **Total** | **769** | **24** |

### Key Wins

1. **`time_select_options` macro**: Saved 120+ lines in polls.html
2. **`seasonal_history_card` macro**: Saved 130+ lines across templates
3. **`DeleteConfirmationManager` class**: Eliminated 269 lines of JS duplication
4. **`delete_entity()` helper**: Eliminated 155 lines of backend duplication

### Code Quality Improvements

- **Type Safety**: 100% type annotations in Python
- **Consistency**: Single source of truth for common patterns
- **Maintainability**: Changes in one place affect all uses
- **Scalability**: Adding polls/users/events doesn't grow code size

---

## Related Documentation

- [templates/components/README.md](../templates/components/README.md) - Detailed macro usage
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Guidelines for creating components
- [REFACTORING_PROGRESS.md](./REFACTORING_PROGRESS.md) - Refactoring project status
- [CLAUDE.md](../CLAUDE.md) - Project architecture and standards

---

**Last Updated**: 2025-11-24
**Phase**: 5 - Component Library & Documentation
**Status**: Living document - update as components evolve
