# API Reference - SABC Tournament Management

## Overview

This document provides a comprehensive reference for all API endpoints in the SABC Tournament Management System. The application uses a hybrid approach with both HTML page routes and JSON API endpoints.

**Interactive Documentation**: When the server is running, visit:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Spec**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Public Pages](#public-pages)
3. [Member Pages](#member-pages)
4. [Admin Routes](#admin-routes)
5. [JSON API Endpoints](#json-api-endpoints)
6. [Monitoring Endpoints](#monitoring-endpoints)
7. [Error Responses](#error-responses)

---

## Authentication

### Login

Authenticate a user and create a session.

```http
GET /login
```
Returns the login page.

```http
POST /login
Content-Type: application/x-www-form-urlencoded

email=user@example.com&password=secret&csrf_token=xxx
```

**Response**:
- `302` - Redirect to homepage on success
- `200` - Login page with error message on failure

---

### Logout

End the current user session.

```http
POST /logout
```

**Response**:
- `302` - Redirect to homepage

---

### Register

Create a new user account.

```http
GET /register
```
Returns the registration page.

```http
POST /register
Content-Type: application/x-www-form-urlencoded

first_name=John&last_name=Doe&email=john@example.com&password=SecurePass123!&csrf_token=xxx
```

**Response**:
- `302` - Redirect to login on success
- `200` - Registration page with error on failure

---

### Password Reset

Request a password reset email.

```http
GET /forgot-password
```
Returns the password reset request page.

```http
POST /forgot-password
Content-Type: application/x-www-form-urlencoded

email=user@example.com&csrf_token=xxx
```

**Response**:
- `302` - Redirect with success message

---

### Reset Password (with token)

Reset password using email token.

```http
GET /reset-password/{token}
```
Returns the password reset form if token is valid.

```http
POST /reset-password/{token}
Content-Type: application/x-www-form-urlencoded

password=NewSecurePass123!&confirm_password=NewSecurePass123!&csrf_token=xxx
```

**Response**:
- `302` - Redirect to login on success
- `200` - Reset page with error on invalid token/password

---

## Public Pages

These routes are accessible to all users (authenticated or not).

### Homepage

```http
GET /
```

Returns the main landing page with:
- Club news and announcements
- Upcoming tournaments
- Recent results

---

### About Page

```http
GET /about
```

Returns information about the South Austin Bass Club.

---

### Calendar

```http
GET /calendar
```

Returns the tournament calendar with:
- Upcoming events
- Past event results
- Event details

---

### Bylaws

```http
GET /bylaws
```

Returns the club bylaws and rules.

---

### Awards & Standings

```http
GET /awards
GET /awards?year=2024
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| year | integer | current year | Year for standings |

Returns:
- Angler of the Year standings
- Big Bass of the Year
- Historical award winners

---

### Tournament Results

```http
GET /results/{event_id}
```

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| event_id | integer | Event ID |

Returns detailed tournament results including:
- Final standings
- Weights and points
- Big bass winner

---

### Club Data Dashboard

```http
GET /data
```

Returns club statistics and analytics:
- Tournament participation trends
- Weight statistics by year
- Lake performance data
- Big bass records

---

## Member Pages

These routes require authentication (member or admin).

### Profile

```http
GET /profile
```

**Authentication**: Required (any authenticated user)

Returns the user's profile page with:
- Personal information
- Tournament history
- Monthly weight chart

```http
POST /profile
Content-Type: application/x-www-form-urlencoded

first_name=John&last_name=Doe&phone=(512) 555-1234&csrf_token=xxx
```

**Authentication**: Required

Updates the user's profile information.

---

### Roster

```http
GET /roster
```

**Authentication**: Required (member or admin)

Returns the member roster with:
- Member list with contact info
- Tournament statistics per member
- Expandable charts per member

---

### Polls

```http
GET /polls
```

**Authentication**: Required (member or admin)

Returns available polls:
- Active polls (can vote)
- Closed polls (view results)

---

### Vote

```http
GET /polls/{poll_id}
```

**Authentication**: Required (member)

Returns poll details and voting form.

```http
POST /polls/{poll_id}/vote
Content-Type: application/x-www-form-urlencoded

option_id=123&csrf_token=xxx
```

**Authentication**: Required (member)

**Response**:
- `302` - Redirect to polls page on success
- `403` - If not a member or already voted

---

### Enter Tournament Results

```http
GET /tournaments/{tournament_id}/enter-results
```

**Authentication**: Required (member or admin)

Returns the results entry form.

```http
POST /tournaments/{tournament_id}/enter-results
Content-Type: application/json

{
  "results": [
    {"angler_id": 1, "total_weight": 15.5, "big_bass": 5.2, "fish_count": 5},
    {"angler_id": 2, "total_weight": 12.3, "big_bass": null, "fish_count": 4}
  ]
}
```

**Authentication**: Required

Submits tournament results.

---

## Admin Routes

All admin routes require admin authentication.

### Admin Dashboard

```http
GET /admin
```

**Authentication**: Admin required

Returns the admin dashboard with:
- Quick stats
- Recent activity
- Management links

---

### User Management

#### List Users

```http
GET /admin/users
```

Returns paginated user list with management controls.

#### Edit User

```http
GET /admin/users/{user_id}
```

Returns user edit form.

```http
POST /admin/users/{user_id}
Content-Type: application/x-www-form-urlencoded

name=John+Doe&email=john@example.com&member=true&is_admin=false&csrf_token=xxx
```

Updates user information.

#### Delete User

```http
DELETE /admin/users/{user_id}
```

**Response**:
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

---

### Event Management

#### List Events

```http
GET /admin/events
GET /admin/events?year=2024
```

Returns event list with management controls.

#### Create Event

```http
GET /admin/events/create
```

Returns event creation form.

```http
POST /admin/events/create
Content-Type: application/x-www-form-urlencoded

date=2024-03-15&name=March+Tournament&event_type=tournament&csrf_token=xxx
```

Creates a new event.

#### Edit Event

```http
POST /admin/events/{event_id}
Content-Type: application/x-www-form-urlencoded

date=2024-03-16&name=March+Tournament+Updated&csrf_token=xxx
```

Updates an existing event.

#### Delete Event

```http
DELETE /admin/events/{event_id}
```

**Response**:
```json
{
  "success": true,
  "message": "Event deleted successfully"
}
```

---

### Tournament Management

#### List Tournaments

```http
GET /admin/tournaments
```

Returns tournament list.

#### Create Tournament

```http
POST /admin/tournaments/create
Content-Type: application/x-www-form-urlencoded

event_id=123&lake_id=1&ramp_id=3&entry_fee=25.00&csrf_token=xxx
```

Creates a tournament for an event.

#### Edit Tournament

```http
POST /admin/tournaments/{tournament_id}
Content-Type: application/x-www-form-urlencoded

lake_id=2&ramp_id=5&complete=true&csrf_token=xxx
```

Updates tournament details.

#### Delete Tournament

```http
DELETE /admin/tournaments/{tournament_id}
```

---

### Poll Management

#### List Polls

```http
GET /admin/polls
```

Returns all polls with management controls.

#### Create Poll

```http
GET /admin/polls/create
GET /admin/polls/create?event_id=123
```

Returns poll creation form.

```http
POST /admin/polls/create
Content-Type: application/x-www-form-urlencoded

event_id=123&title=March+Location+Vote&poll_type=tournament_location&starts_at=2024-03-01T09:00&closes_at=2024-03-08T17:00&options=Lake+Travis|Lake+Austin&csrf_token=xxx
```

Creates a new poll.

#### Delete Poll

```http
DELETE /admin/polls/{poll_id}
```

Deletes a poll and all associated votes/options.

---

### Lake Management

#### List Lakes

```http
GET /admin/lakes
```

Returns lake list with management controls.

#### Create Lake

```http
POST /admin/lakes/create
Content-Type: application/x-www-form-urlencoded

name=Lake+Travis&location=Travis+County,+TX&csrf_token=xxx
```

#### Edit Lake

```http
POST /admin/lakes/{lake_id}
Content-Type: application/x-www-form-urlencoded

name=Lake+Travis+Updated&location=Austin,+TX&csrf_token=xxx
```

#### Delete Lake

```http
DELETE /admin/lakes/{lake_id}
```

**Note**: Will fail if lake is referenced by tournaments.

---

### Ramp Management

#### List Ramps

```http
GET /admin/ramps
GET /admin/lakes/{lake_id}/ramps
```

Returns ramp list.

#### Create Ramp

```http
POST /admin/ramps/create
Content-Type: application/x-www-form-urlencoded

lake_id=1&name=Mansfield+Dam&coordinates=30.3900,-97.9000&csrf_token=xxx
```

#### Delete Ramp

```http
DELETE /admin/ramps/{ramp_id}
```

---

### News Management

#### Create News

```http
POST /admin/news/create
Content-Type: application/x-www-form-urlencoded

title=March+Meeting+Announcement&content=Meeting+will+be+held...&published=true&priority=normal&csrf_token=xxx
```

#### Edit News

```http
POST /admin/news/{news_id}
Content-Type: application/x-www-form-urlencoded

title=Updated+Title&content=Updated+content&csrf_token=xxx
```

#### Delete News

```http
DELETE /admin/news/{news_id}
```

---

## JSON API Endpoints

These endpoints return JSON responses for AJAX/HTMX requests.

### Get Ramps by Lake

```http
GET /api/lakes/{lake_id}/ramps
```

**Response**:
```json
{
  "ramps": [
    {"id": 1, "name": "Mansfield Dam", "coordinates": "30.3900,-97.9000"},
    {"id": 2, "name": "Pace Bend", "coordinates": "30.4500,-97.9500"}
  ]
}
```

---

### Get Poll Results

```http
GET /api/polls/{poll_id}/results
```

**Authentication**: Required (member or admin)

**Response**:
```json
{
  "poll_id": 123,
  "title": "March Tournament Location",
  "total_votes": 15,
  "options": [
    {"id": 1, "text": "Lake Travis - Mansfield Dam", "votes": 8, "percentage": 53.3},
    {"id": 2, "text": "Lake Austin - Walsh Landing", "votes": 7, "percentage": 46.7}
  ],
  "winner": {"id": 1, "text": "Lake Travis - Mansfield Dam"}
}
```

---

### Get Tournament Statistics

```http
GET /api/tournaments/{tournament_id}/stats
```

**Response**:
```json
{
  "tournament_id": 123,
  "total_weight": 245.5,
  "total_fish": 48,
  "participants": 12,
  "limits": 3,
  "zeros": 1,
  "average_weight": 20.46,
  "big_bass": {"weight": 6.25, "angler": "John Doe"}
}
```

---

### Check Username/Email Availability

```http
GET /api/check-email?email=user@example.com
```

**Response**:
```json
{
  "available": true
}
```

---

## Monitoring Endpoints

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-03-15T10:30:00Z"
}
```

Used for uptime monitoring and load balancer health checks.

---

### Prometheus Metrics

```http
GET /metrics
```

**Response**: Prometheus text format

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/",status="200"} 1234

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/",le="0.1"} 1200
```

**Warning**: Restrict access to this endpoint in production via firewall rules.

---

## Error Responses

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Request successful |
| 302 | Redirect | Form submission success |
| 400 | Bad Request | Invalid form data |
| 401 | Unauthorized | Not authenticated |
| 403 | Forbidden | Insufficient permissions, CSRF failure |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Pydantic validation failure |
| 500 | Server Error | Internal error |

### Error Response Format

**HTML Routes** (form submissions):
- Redirect with error query parameter: `/form?error=Error+message`
- Re-render page with error in template context

**JSON API Routes**:
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

### CSRF Errors

```http
POST /any-form-endpoint
# Without csrf_token or with invalid token

HTTP/1.1 403 Forbidden
```

**Resolution**: Include valid CSRF token from the form.

---

## Request Headers

### Required Headers

| Header | Value | Required For |
|--------|-------|--------------|
| Content-Type | application/x-www-form-urlencoded | Form submissions |
| Content-Type | application/json | JSON API requests |
| Cookie | session=xxx | Authenticated requests |

### CSRF Protection

All POST/PUT/DELETE requests require a valid CSRF token. Include the token:

**Form submissions**:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
```

**AJAX requests**:
```javascript
const csrfToken = getCsrfToken(); // From utils.js
fetch('/api/endpoint', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': csrfToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
});
```

---

## Rate Limiting

Authentication endpoints have rate limiting to prevent brute force attacks:

| Endpoint | Limit |
|----------|-------|
| POST /login | 10 requests per minute |
| POST /forgot-password | 5 requests per minute |
| POST /register | 5 requests per minute |

Exceeding the limit returns:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

---

## Pagination

Endpoints returning lists support pagination:

```http
GET /admin/users?page=1&per_page=25
```

**Query Parameters**:
| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| page | integer | 1 | - | Page number (1-indexed) |
| per_page | integer | 25 | 100 | Items per page |

**Response includes**:
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total_items": 150,
    "total_pages": 6,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## Filtering and Sorting

Many list endpoints support filtering:

```http
GET /admin/events?year=2024&event_type=tournament
GET /admin/users?member=true&sort=name&order=asc
```

**Common Filter Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| year | integer | Filter by year |
| member | boolean | Filter by membership status |
| sort | string | Field to sort by |
| order | string | Sort order (asc/desc) |

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guidelines
- [TESTING.md](TESTING.md) - Testing API endpoints

---

**Last Updated**: 2024-11-30
