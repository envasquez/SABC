# Testing TODO - Remaining Work

## Current Status: 296/328 Tests Passing (90.2%) ✅

This document tracks the remaining 29 failing tests that need to be fixed in follow-up PRs.

---

## Summary by Category

| Category | Count | Priority |
|----------|-------|----------|
| Voting Workflow | ~15 | HIGH |
| Data Rendering | ~8 | MEDIUM |
| Admin Features | ~4 | MEDIUM |
| Calculations | ~2 | LOW |
| **TOTAL** | **29** | |

---

## 1. Voting Workflow Issues (~15 tests) - HIGH PRIORITY

**Files**: `tests/integration/test_poll_voting_e2e.py`

### Failing Tests:
- `test_member_can_cast_vote_on_simple_poll`
- `test_member_can_vote_on_tournament_location_poll`
- `test_member_cannot_vote_twice_on_same_poll`
- `test_member_cannot_vote_on_closed_poll`
- `test_member_cannot_vote_on_future_poll`
- `test_member_cannot_vote_with_invalid_poll`
- `test_member_cannot_vote_with_invalid_option`
- `test_unauthenticated_user_cannot_vote`
- `test_non_member_cannot_access_polls`
- `test_admin_can_cast_proxy_vote_for_member`
- `test_admin_cannot_proxy_vote_for_non_member`
- `test_non_admin_cannot_cast_proxy_vote`

### Root Causes:
1. **Permission checks not working correctly** - Routes returning wrong status codes
2. **Vote submission logic issues** - Votes not being recorded properly
3. **Proxy voting not implemented** - Admin proxy vote functionality missing/broken

### Action Items:
- [ ] Review `routes/voting/vote_poll.py` permission checks
- [ ] Fix member-only access validation
- [ ] Implement/fix proxy voting for admins
- [ ] Ensure proper error responses (403 vs 302 redirects)
- [ ] Add validation for poll status (open/closed/future)

---

## 2. Data Rendering Issues (~8 tests) - MEDIUM PRIORITY

**Files**: `tests/integration/test_home_page_workflows.py`, `tests/integration/test_template_rendering.py`

### Failing Tests:
- `test_home_page_shows_upcoming_events`
- `test_home_page_shows_aoy_standings_when_available`
- `test_home_page_navigation_shows_correct_links_for_anonymous`
- `test_roster_shows_club_members`
- `test_awards_page_shows_tournament_results`
- `test_tournament_results_shows_rankings`
- `test_individual_tournament_results_page_accessible`
- `test_all_admin_routes`

### Root Causes:
1. **Query filters too restrictive** - Events/tournaments created in tests don't match filters
2. **Template conditional logic** - Some content only shows under specific conditions
3. **Data aggregation issues** - AOY standings, rankings not calculating correctly

### Action Items:
- [ ] Review `routes/pages/home.py` query logic for upcoming events
- [ ] Check `routes/pages/roster.py` member filtering
- [ ] Fix AOY standings calculation/display
- [ ] Verify tournament results queries include test data
- [ ] Check navigation template conditions for anonymous users

---

## 3. Admin Features (~4 tests) - MEDIUM PRIORITY

**Files**: `tests/integration/test_tournament_admin_workflows.py`

### Failing Tests:
- `test_admin_can_view_tournaments_list`
- `test_admin_tournaments_page_renders`
- `test_admin_can_enter_team_results`
- `test_admin_can_delete_individual_result`

### Root Causes:
1. **Admin routes partially implemented** - Some GET routes exist but missing POST handlers
2. **Team results entry** - Logic may not be complete
3. **Result deletion** - DELETE handler may have issues

### Action Items:
- [ ] Implement `/admin/tournaments` list page fully
- [ ] Fix team results entry in `routes/admin/tournaments/team_results.py`
- [ ] Debug result deletion in `routes/admin/tournaments/manage_results.py`
- [ ] Ensure proper redirects after admin actions

---

## 4. Calculation Logic (~2 tests) - LOW PRIORITY

**Files**: `tests/integration/test_tournament_admin_workflows.py`

### Failing Tests:
- `test_admin_can_enter_results_with_dead_fish_penalty`
- `test_results_with_penalty_show_net_weight`

### Root Causes:
1. **Dead fish penalty not calculated** - Test expects penalty of 0.25 per dead fish, getting 0.0
2. **Net weight display** - Penalty should be subtracted from total weight in results

### Action Items:
- [ ] Review `routes/admin/tournaments/individual_results.py` penalty calculation
- [ ] Check if `dead_fish_penalty` is being applied to weight calculations
- [ ] Verify tournament results template shows net weight (total - penalty)

---

## Recommended Approach

### PR #2: Fix Voting Workflows (15 tests)
**Impact**: Highest - voting is core functionality
**Effort**: Medium (2-3 hours)
**Files**: `routes/voting/*`

### PR #3: Fix Data Rendering (8 tests)
**Impact**: Medium - affects user experience
**Effort**: Medium (2-3 hours)
**Files**: `routes/pages/*`, templates

### PR #4: Fix Admin Features (4 tests)
**Impact**: Medium - admin-only functionality
**Effort**: Low (1-2 hours)
**Files**: `routes/admin/tournaments/*`

### PR #5: Fix Calculations (2 tests)
**Impact**: Low - edge case feature
**Effort**: Low (30 min - 1 hour)
**Files**: `routes/admin/tournaments/individual_results.py`

---

## Running Tests for Each Category

```bash
# Voting tests
nix develop -c pytest tests/integration/test_poll_voting_e2e.py -v

# Data rendering tests
nix develop -c pytest tests/integration/test_home_page_workflows.py -v
nix develop -c pytest tests/integration/test_template_rendering.py -v

# Admin features tests
nix develop -c pytest tests/integration/test_tournament_admin_workflows.py::TestAdminDashboardAccess -v
nix develop -c pytest tests/integration/test_tournament_admin_workflows.py::TestTeamResultsEntry -v

# Calculation tests
nix develop -c pytest tests/integration/test_tournament_admin_workflows.py::TestDeadFishPenalties -v

# All integration tests
nix develop -c pytest tests/integration/ -v

# Full test suite
nix develop -c pytest tests/ -v
```

---

## Notes

- All test infrastructure is now solid ✅
- Code quality checks all passing ✅
- These are legitimate application bugs/incomplete features
- Each category can be tackled independently
- Estimated total time: 6-9 hours to reach 100% passing

---

**Last Updated**: 2025-11-17
**Current Coverage**: 90.2% (296/328 tests passing)
**Target**: 100% (328/328 tests passing)
