# Dues Management Feature Implementation Plan

## Context

**Problem**: Members currently retain voting privileges year-round even without paying annual dues. This creates a "limbo period" at year-end where last year's members vote on January tournaments without being paid members for the current year.

**Goal**: Implement dues tracking that:
- Expires all memberships at year-end (Dec 31)
- Blocks voting for lapsed members while preserving site access
- Shows a dismissable banner that reappears when new polls are created
- Provides admin UI to mark dues as paid

---

## Files to Modify

| File | Change |
|------|--------|
| [core/db_schema/models.py](../core/db_schema/models.py) | Add `dues_paid_through` and `dues_banner_dismissed_at` fields to Angler |
| [core/helpers/auth.py](../core/helpers/auth.py) | Add `is_dues_current()` helper function |
| [core/query_service/user_queries.py](../core/query_service/user_queries.py) | Add new fields to `ALLOWED_UPDATE_COLUMNS` |
| [core/query_service/poll_queries.py](../core/query_service/poll_queries.py) | Add `get_latest_poll_created_at()` method |
| [routes/voting/vote_poll.py](../routes/voting/vote_poll.py) | Add dues check before allowing vote + dismiss endpoint |
| [routes/voting/list_polls.py](../routes/voting/list_polls.py) | Calculate and pass `show_dues_banner` to template |
| [templates/polls.html](../templates/polls.html) | Add dismissable dues banner after line 19 |
| [routes/admin/users/edit_user.py](../routes/admin/users/edit_user.py) | Include `dues_paid_through` in edit form data |
| [routes/admin/users/update_user/save.py](../routes/admin/users/update_user/save.py) | Handle `dues_paid_through` form field |
| [templates/admin/edit_user.html](../templates/admin/edit_user.html) | Add dues date picker field |
| New: `alembic/versions/xxx_add_dues_tracking.py` | Database migration |

---

## Implementation Phases

### Phase 1: Database Foundation
- Create Alembic migration to add `dues_paid_through` (Date) and `dues_banner_dismissed_at` (DateTime) columns to `anglers` table
- Update `Angler` model in `models.py` with new fields
- Update `ALLOWED_UPDATE_COLUMNS` in user_queries.py

### Phase 2: Core Logic
- Add `is_dues_current()` helper function to `auth.py`
- Add `get_latest_poll_created_at()` method to poll_queries.py
- Update voting logic in `vote_poll.py` to check dues status (admins bypass)

### Phase 3: User-Facing Banner
- Add banner dismiss endpoint to `vote_poll.py`
- Calculate `show_dues_banner` in `list_polls.py`
- Add dismissable banner to `polls.html` template

### Phase 4: Admin UI
- Update `edit_user.py` to include `dues_paid_through` in form data
- Update `save.py` to handle `dues_paid_through` form field
- Add date picker to `edit_user.html` template with current/expired status indicator

---

## Access Control Matrix

| User Type | Site Access | Can Vote | Sees Banner |
|-----------|-------------|----------|-------------|
| Guest (never member) | Public only | No | No |
| Lapsed member | Full site | **No** | Yes (smart) |
| Current member | Full site | Yes | No |
| Admin (lapsed) | Full site | **Yes** | No |

**Note**: Admins bypass dues check and can always vote. Banner only appears on /polls page.

---

## Technical Details

### Database Migration
```python
op.add_column("anglers", sa.Column("dues_paid_through", sa.Date(), nullable=True))
op.add_column("anglers", sa.Column("dues_banner_dismissed_at", sa.DateTime(timezone=True), nullable=True))
```

### Model Fields
```python
dues_paid_through: Mapped[Optional[date]] = mapped_column(Date)
dues_banner_dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
```

### Auth Helper
```python
def is_dues_current(user: UserDict) -> bool:
    """Check if user's dues are paid through today or later."""
    dues_paid_through = user.get("dues_paid_through")
    if dues_paid_through is None:
        return False
    if isinstance(dues_paid_through, str):
        dues_paid_through = date.fromisoformat(dues_paid_through)
    return dues_paid_through >= date.today()
```

### Voting Check
```python
# Admins can always vote; regular members need current dues
if not user.get("is_admin") and not is_dues_current(user):
    return RedirectResponse(
        "/polls?error=Your dues have expired. Please pay your annual dues, in order to vote.",
        status_code=303
    )
```

### Banner Logic
```python
show_dues_banner = False
if (user and user.get("member")
    and not user.get("is_admin")
    and not is_dues_current(user)):

    dismissed_at = user.get("dues_banner_dismissed_at")
    latest_poll_created = qs.get_latest_poll_created_at()

    if dismissed_at is None:
        show_dues_banner = True
    elif latest_poll_created and latest_poll_created > dismissed_at:
        show_dues_banner = True  # New poll since dismissal
```

### Banner Template
```html
{% if show_dues_banner %}
<div class="alert alert-warning alert-dismissible fade show" role="alert">
    <i class="bi bi-exclamation-triangle-fill me-2"></i>
    <strong>Dues Required:</strong> Your club dues have expired.
    Please pay your annual dues to vote in polls.
    <form method="POST" action="/dismiss-dues-banner" class="d-inline">
        {{ csrf_token(request) }}
        <button type="submit" class="btn-close" aria-label="Dismiss"></button>
    </form>
</div>
{% endif %}
```

---

## Verification Steps

1. **Run migration**: `alembic upgrade head`
2. **Run checks**: `nix develop -c format-code && nix develop -c check-code && nix develop -c run-tests`
3. **Manual testing**:
   - Set a member's `dues_paid_through` to past date via admin UI
   - Log in as that member - verify banner appears on /polls
   - Try to vote - should get error message
   - Dismiss banner - should disappear
   - Create new poll as admin
   - Log back in as lapsed member - banner should reappear
   - Set `dues_paid_through` to future date
   - Verify banner gone and voting works

---

## Edge Cases

- `dues_paid_through = NULL` → treated as expired (never paid)
- `dues_paid_through = today` → treated as current (expires at midnight)
- Admin with lapsed dues → **can still vote** (admin privilege)
- Proxy voting by admin → should check target member's dues status (not admin's)
