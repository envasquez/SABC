# SABC Template Components

This directory contains documentation for all reusable Jinja2 template components (macros) used in the SABC application.

## Overview

All macros are defined in [`templates/macros.html`](../macros.html) and imported into templates via:

```jinja2
{% from "macros.html" import macro_name %}
```

## Component Categories

### 1. Security & Forms
- [`csrf_token`](#csrf_token) - CSRF protection tokens

### 2. User Interface
- [`alert`](#alert) - Alert/notification messages
- [`badge`](#badge) - Generic badge component
- [`officer_badge`](#officer_badge) - Officer position badges
- [`member_badge`](#member_badge) - Member status indicators

### 3. Forms & Inputs
- [`form_field`](#form_field) - Form input fields with labels
- [`time_select_options`](#time_select_options) - Time dropdown options

### 4. Containers & Layout
- [`card`](#card) - Bootstrap card containers
- [`modal`](#modal) - Bootstrap modal dialogs
- [`delete_modal`](#delete_modal) - Delete confirmation modals
- [`stat_card`](#stat_card) - Statistics display cards
- [`seasonal_history_card`](#seasonal_history_card) - Tournament history cards

---

## Component Reference

### csrf_token

**Purpose**: Generates a hidden CSRF token input field for form security.

**Parameters**:
- `request` (Request) - FastAPI request object

**Usage**:
```jinja2
{% from "macros.html" import csrf_token %}

<form method="POST" action="/submit">
    {{ csrf_token(request) }}
    <!-- other form fields -->
</form>
```

**Output**:
```html
<input type="hidden" name="csrf_token" value="abc123...">
```

**Notes**:
- Required in ALL POST forms
- Token automatically validated by middleware
- Never omit CSRF tokens from forms

---

### alert

**Purpose**: Displays Bootstrap alert messages with optional dismiss button.

**Parameters**:
- `type` (str) - Alert type: 'success', 'danger', 'warning', 'info'
- `message` (str) - Alert message text
- `dismissible` (bool, default=True) - Show dismiss button

**Usage**:
```jinja2
{% from "macros.html" import alert %}

{{ alert('success', 'Tournament results saved successfully!') }}
{{ alert('danger', 'Failed to delete user', dismissible=False) }}
{{ alert('warning', 'This tournament is not yet complete') }}
{{ alert('info', 'Poll closes in 2 hours', dismissible=False) }}
```

**Output**:
```html
<div class="alert alert-success alert-dismissible fade show" role="alert">
    Tournament results saved successfully!
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
```

**Notes**:
- Uses Bootstrap 5 alert styles
- Non-dismissible alerts stay visible until page reload
- Commonly used with URL query parameters: `?success=Message` or `?error=Message`

---

### form_field

**Purpose**: Generates a labeled form input field with Bootstrap styling.

**Parameters**:
- `label` (str) - Field label text
- `name` (str) - Input name attribute
- `type` (str, default='text') - Input type: 'text', 'email', 'password', 'number', 'date', 'time', 'tel'
- `value` (str, default='') - Pre-filled value
- `required` (bool, default=False) - HTML5 required attribute
- `placeholder` (str, default='') - Placeholder text
- `help_text` (str, default='') - Help text below field
- `min` (str, default='') - Min value for number/date inputs
- `max` (str, default='') - Max value for number/date inputs
- `step` (str, default='') - Step value for number inputs

**Usage**:
```jinja2
{% from "macros.html" import form_field %}

{{ form_field('Email Address', 'email', type='email', required=True) }}
{{ form_field('Event Date', 'event_date', type='date', value='2025-01-15') }}
{{ form_field('Max Participants', 'max_participants', type='number', min='1', max='50') }}
{{ form_field('Phone', 'phone', type='tel', placeholder='512-555-0123',
              help_text='Format: XXX-XXX-XXXX') }}
```

**Output**:
```html
<div class="mb-3">
    <label for="email" class="form-label">Email Address</label>
    <input type="email" class="form-control" id="email" name="email" required>
</div>
```

**Notes**:
- Automatically generates matching `id` and `name` attributes
- Uses Bootstrap 5 form styling
- Help text displayed in muted text below field

---

### card

**Purpose**: Creates a Bootstrap card container with optional header and footer.

**Parameters**:
- `title` (str, default='') - Card header title
- `header_class` (str, default='bg-primary text-white') - Header CSS classes
- `body_class` (str, default='') - Body CSS classes
- `footer` (str, default='') - Footer content (HTML)

**Usage**:
```jinja2
{% from "macros.html" import card %}

{% call card(title='Tournament Results', header_class='bg-success text-white') %}
    <p>Results content here...</p>
    <table class="table">...</table>
{% endcall %}

{% call card(body_class='text-center') %}
    <h3>No header card</h3>
    <p>Card with custom body styling</p>
{% endcall %}
```

**Output**:
```html
<div class="card mb-3">
    <div class="card-header bg-success text-white">
        <h5 class="mb-0">Tournament Results</h5>
    </div>
    <div class="card-body">
        <p>Results content here...</p>
        <table class="table">...</table>
    </div>
</div>
```

**Notes**:
- Uses Jinja2 `{% call %}` block syntax
- Header only rendered if `title` provided
- Footer only rendered if `footer` provided

---

### modal

**Purpose**: Creates a Bootstrap modal dialog.

**Parameters**:
- `id` (str) - Unique modal ID
- `title` (str) - Modal header title
- `size` (str, default='') - Modal size: '', 'modal-lg', 'modal-xl', 'modal-sm'

**Usage**:
```jinja2
{% from "macros.html" import modal %}

{% call modal('detailsModal', 'Angler Details', size='modal-lg') %}
    <p>Modal body content here...</p>
    <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
    </div>
{% endcall %}

<button data-bs-toggle="modal" data-bs-target="#detailsModal">Show Details</button>
```

**Output**:
```html
<div class="modal fade" id="detailsModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Angler Details</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p>Modal body content here...</p>
            </div>
        </div>
    </div>
</div>
```

**Notes**:
- Trigger with `data-bs-toggle="modal" data-bs-target="#modalId"`
- Or use JavaScript: `new bootstrap.Modal(document.getElementById('modalId')).show()`
- Modal footer should be included in the call block if needed

---

### badge

**Purpose**: Creates a Bootstrap badge with optional icon.

**Parameters**:
- `text` (str) - Badge text
- `color` (str, default='primary') - Bootstrap color: 'primary', 'success', 'danger', 'warning', 'info', 'secondary'
- `icon` (str, default='') - Bootstrap icon class (without 'bi-' prefix)

**Usage**:
```jinja2
{% from "macros.html" import badge %}

{{ badge('Active', 'success', 'check-circle') }}
{{ badge('Pending', 'warning') }}
{{ badge('3 votes', 'info', 'hand-thumbs-up') }}
```

**Output**:
```html
<span class="badge bg-success">
    <i class="bi bi-check-circle"></i> Active
</span>
```

**Notes**:
- Uses Bootstrap Icons (requires Bootstrap Icons CSS)
- Color maps to Bootstrap badge background colors

---

### officer_badge

**Purpose**: Displays a formatted badge for officer positions.

**Parameters**:
- `position` (str) - Officer position name

**Usage**:
```jinja2
{% from "macros.html" import officer_badge %}

{{ officer_badge('President') }}
{{ officer_badge('Vice President') }}
{{ officer_badge('Treasurer') }}
```

**Output**:
```html
<span class="badge bg-primary">
    <i class="bi bi-star-fill"></i> President
</span>
```

**Notes**:
- Always uses primary color with star icon
- Consistent styling for all officer positions

---

### member_badge

**Purpose**: Displays member status indicator.

**Parameters**:
- `is_member` (bool) - True if user is a verified member

**Usage**:
```jinja2
{% from "macros.html" import member_badge %}

{{ member_badge(angler.member) }}
```

**Output (member)**:
```html
<span class="badge bg-success">
    <i class="bi bi-check-circle-fill"></i> Member
</span>
```

**Output (non-member)**:
```html
<span class="badge bg-secondary">
    <i class="bi bi-x-circle"></i> Not a Member
</span>
```

**Notes**:
- Green badge for members, gray for non-members
- Used in user lists and profile displays

---

### stat_card

**Purpose**: Displays a statistic with icon in a card format.

**Parameters**:
- `icon` (str) - Bootstrap icon class (without 'bi-' prefix)
- `title` (str) - Statistic title
- `value` (str|number) - Statistic value
- `color` (str, default='primary') - Bootstrap color for icon background

**Usage**:
```jinja2
{% from "macros.html" import stat_card %}

<div class="row">
    <div class="col-md-3">
        {{ stat_card('trophy', 'Total Tournaments', tournament_count, 'success') }}
    </div>
    <div class="col-md-3">
        {{ stat_card('people', 'Active Members', member_count, 'info') }}
    </div>
    <div class="col-md-3">
        {{ stat_card('calendar-event', 'Upcoming Events', event_count, 'warning') }}
    </div>
</div>
```

**Output**:
```html
<div class="card text-center">
    <div class="card-body">
        <div class="display-4 text-success mb-3">
            <i class="bi bi-trophy"></i>
        </div>
        <h5 class="card-title">Total Tournaments</h5>
        <p class="display-6 mb-0">24</p>
    </div>
</div>
```

**Notes**:
- Best used in grid layouts (Bootstrap columns)
- Icon uses display-4 size, value uses display-6
- Commonly used on dashboard and statistics pages

---

### delete_modal

**Purpose**: Creates a standardized delete confirmation modal with form.

**Parameters**:
- `modal_id` (str) - Unique modal ID
- `title` (str) - Modal title (e.g., "Delete User")
- `message` (str) - Confirmation message
- `form_action` (str) - Form submission URL
- `item_name` (str, default='') - Name of item being deleted (shown in message)
- `csrf_token_value` (str) - CSRF token value

**Usage**:
```jinja2
{% from "macros.html" import delete_modal %}

{{ delete_modal(
    modal_id='deleteUserModal',
    title='Delete User',
    message='Are you sure you want to delete this user account? This action cannot be undone.',
    form_action='/admin/users/' ~ user.id ~ '/delete',
    item_name=user.name,
    csrf_token_value=csrf_token
) }}

<button data-bs-toggle="modal" data-bs-target="#deleteUserModal" class="btn btn-danger">
    Delete User
</button>
```

**Output**:
```html
<div class="modal fade" id="deleteUserModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Delete User</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p>Are you sure you want to delete this user account? This action cannot be undone.</p>
                <p><strong>User: John Smith</strong></p>
            </div>
            <div class="modal-footer">
                <form method="POST" action="/admin/users/123/delete">
                    <input type="hidden" name="csrf_token" value="...">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-danger">Delete</button>
                </form>
            </div>
        </div>
    </div>
</div>
```

**Notes**:
- Uses POST method with CSRF token
- Consistent danger styling for delete actions
- Item name displayed in bold if provided
- Cancel button dismisses modal without action

---

### time_select_options

**Purpose**: Generates `<option>` elements for time selection dropdowns.

**Parameters**:
- `start_hour` (int, default=5) - Starting hour (0-23)
- `end_hour` (int, default=21) - Ending hour (0-23)
- `interval_minutes` (int, default=15) - Interval between times
- `selected_time` (str, default='') - Pre-selected time in 'HH:MM' format

**Usage**:
```jinja2
{% from "macros.html" import time_select_options %}

<select name="start_time" class="form-select">
    <option value="">Select start time</option>
    {{ time_select_options(start_hour=6, end_hour=10, selected_time='07:00') }}
</select>

<select name="end_time" class="form-select">
    <option value="">Select end time</option>
    {{ time_select_options(start_hour=12, end_hour=18, interval_minutes=30, selected_time='15:00') }}
</select>
```

**Output**:
```html
<option value="06:00">6:00 AM</option>
<option value="07:00" selected>7:00 AM</option>
<option value="08:00">8:00 AM</option>
...
```

**Notes**:
- Generates times in 12-hour format with AM/PM
- Values stored in 24-hour format (HH:MM)
- Default interval is 15 minutes
- Default range is 5 AM to 9 PM (tournament typical hours)
- **Saved 120+ lines** in polls.html by eliminating per-poll duplication

---

### seasonal_history_card

**Purpose**: Displays a formatted card of seasonal tournament history.

**Parameters**:
- `seasonal_history` (list) - List of dicts with keys: 'season', 'event_count', 'tournament_count', 'member_count'

**Usage**:
```jinja2
{% from "macros.html" import seasonal_history_card %}

{{ seasonal_history_card(seasonal_history) }}
```

**Input Data Structure**:
```python
seasonal_history = [
    {
        'season': '2025',
        'event_count': 12,
        'tournament_count': 10,
        'member_count': 45
    },
    {
        'season': '2024',
        'event_count': 11,
        'tournament_count': 9,
        'member_count': 42
    }
]
```

**Output**:
```html
<div class="card">
    <div class="card-header bg-info text-white">
        <h5 class="mb-0">Seasonal History</h5>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Season</th>
                        <th>Events</th>
                        <th>Tournaments</th>
                        <th>Members</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>2025</strong></td>
                        <td>12</td>
                        <td>10</td>
                        <td>45</td>
                    </tr>
                    ...
                </tbody>
            </table>
        </div>
    </div>
</div>
```

**Notes**:
- Responsive table design
- Most recent season shown first
- Used on dashboard and statistics pages
- **Saved 130+ lines** across multiple templates

---

## Best Practices

### When to Use Macros

✅ **DO use macros for**:
- Repeated UI patterns (cards, badges, alerts)
- Form elements with consistent styling
- Complex HTML structures used multiple times
- Components that need consistent behavior

❌ **DON'T use macros for**:
- One-off unique layouts
- Simple HTML that's not repeated
- Page-specific content structures

### Macro Naming Conventions

- Use descriptive, action-oriented names: `delete_modal`, not `modal2`
- Use underscores, not camelCase: `form_field`, not `formField`
- Prefix specialized variants: `officer_badge`, `member_badge`

### Documentation Requirements

When creating a new macro:
1. Add JSDoc-style comment in macros.html
2. Update this README with usage example
3. Add to appropriate category
4. Include parameter types and defaults
5. Show real-world usage example

### Testing Macros

- Manually test with different parameter combinations
- Check rendering in all supported browsers
- Verify accessibility (ARIA labels, keyboard navigation)
- Test with edge cases (empty strings, None values, long text)

---

## Related Documentation

- [COMPONENTS.md](../../docs/COMPONENTS.md) - Comprehensive component architecture guide
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Guidelines for creating new components
- [REFACTORING_PROGRESS.md](../../docs/REFACTORING_PROGRESS.md) - Refactoring project status

---

## Statistics

**Current Macro Count**: 11 macros
**Lines in macros.html**: 240 lines
**Lines Saved**: 345+ lines across Phase 1 refactoring
**Files Using Macros**: 15+ templates

---

**Last Updated**: 2025-11-24
**Phase**: 5 - Component Library & Documentation
