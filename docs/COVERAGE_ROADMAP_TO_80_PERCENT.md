# Test Coverage Roadmap to 80%

**Current Status**: 68.0% coverage (412 tests passing)
**Goal**: 80% coverage (+12% needed)
**Date**: November 18, 2025

## Executive Summary

We've made excellent progress improving test coverage from **53.5% → 68.0% (+14.5%)**. This document outlines the strategic path to reach our 80% goal.

## Recent Achievements ✅

### Phase 3 (Completed): Security & Critical Bugs
- **Coverage**: 53.5% → 65.8% (+12.3%)
- **Tests Added**: 50+ security and workflow tests
- **Bugs Fixed**: 6 critical security issues (XSS, validation, etc.)

### Phase 4 (Completed): Database Lock Fix
- **Coverage**: 65.8% → 68.0% (+2.2%)
- **Major Fix**: Resolved database locking issue blocking test development
- **Architecture**: Properly enforced Session (writes) vs Connection (reads) pattern
- **Tests Added**: 21 comprehensive admin workflow tests
- **Impact**: Unblocked future test development

## Path to 80% Coverage: Strategic Targets

Based on coverage analysis, here are the highest-ROI targets (ordered by impact):

### Tier 1: Voting System (~2.3% gain)
**Current**: 239 statements, 100 missed
**Files**:
- `routes/voting/helpers.py` (31.6% → target 70%+)
- `routes/voting/vote_poll.py` (71.7% → target 90%+)
- `routes/voting/vote_validation.py` (87.3% → target 95%+)
- `routes/voting/list_polls.py` (83.3% → target 95%+)

**Test Strategy**:
```python
# Focus on these workflows:
1. Proxy voting (admin votes for members)
2. Tournament location voting with structured data
3. Vote change/update scenarios
4. Closed/future poll edge cases
5. Seasonal tournament history display
```

### Tier 2: Admin Tournament Management (~3.7% gain)
**Current**: 239 statements, 158 missed
**Files**:
- `routes/admin/tournaments/manage_results.py` (36.6% → target 85%+)
- `routes/admin/tournaments/individual_results.py` (36.7% → target 85%+)
- `routes/admin/tournaments/team_results.py` (27.1% → target 85%+)
- `routes/admin/tournaments/validation.py` (0% → target 70%+)

**Test Strategy**:
```python
# Focus on these operations:
1. Individual result CRUD (create, update, delete)
2. Team result management (including solo teams)
3. Disqualification and buy-in handling
4. Result validation (negative weights, fish limits)
5. Dead fish penalties
```

### Tier 3: Poll Creation & Editing (~2.5% gain)
**Current**: 150 statements, 108 missed
**Files**:
- `routes/admin/polls/create_poll/handler.py` (28.6% → target 75%+)
- `routes/admin/polls/edit_poll_save.py` (33.3% → target 75%+)
- `routes/admin/polls/create_poll/options.py` (20.5% → target 70%+)

**Test Strategy**:
```python
# Focus on these workflows:
1. Simple poll creation
2. Tournament location poll creation with lake/ramp data
3. Poll editing (title, dates, options)
4. Option management (add, edit, delete)
5. Poll validation edge cases
```

### Tier 4: Helper Functions (~1.5% gain)
**Current**: Various helper modules with 15-40% coverage
**Files**:
- `core/helpers/password_validator.py` (17.4% → target 70%+)
- `core/helpers/sanitize.py` (41.2% → target 75%+)
- `core/helpers/timezone.py` (37.9% → target 75%+)
- `routes/admin/users/email_helpers.py` (9.1% → target 70%+)

**Test Strategy**:
```python
# Simple unit tests:
1. Password strength validation (all rules)
2. HTML sanitization (XSS prevention)
3. Timezone conversions (UTC ↔ local)
4. Email generation (guests, validation)
```

### Tier 5: Page Routes (~2% gain)
**Current**: Public pages with 17-50% coverage
**Files**:
- `routes/pages/home.py` (17.0% → target 60%+)
- `routes/pages/awards.py` (19.7% → target 60%+)
- `routes/pages/calendar.py` (54.5% → target 80%+)
- `routes/pages/roster.py` (44.4% → target 75%+)

**Test Strategy**:
```python
# Integration tests for page loads:
1. Home page with tournaments and news
2. Awards page with standings
3. Calendar page with events
4. Roster page with member list
5. Error handling for missing data
```

## Implementation Plan

### Recommended Order (for maximum impact):

1. **Start with Tier 4 (Helpers)** - Quickest wins, pure unit tests
   - Estimated effort: 2-3 hours
   - Expected gain: ~1.5%
   - No complex setup needed

2. **Then Tier 1 (Voting)** - High value, builds on existing poll tests
   - Estimated effort: 4-6 hours
   - Expected gain: ~2.3%
   - Leverages existing fixtures

3. **Then Tier 5 (Pages)** - Simple integration tests
   - Estimated effort: 3-4 hours
   - Expected gain: ~2%
   - Straightforward GET requests

4. **Then Tier 3 (Poll Admin)** - Medium complexity
   - Estimated effort: 4-5 hours
   - Expected gain: ~2.5%
   - Requires proper Event/Poll fixtures

5. **Finally Tier 2 (Tournament Admin)** - Most complex
   - Estimated effort: 6-8 hours
   - Expected gain: ~3.7%
   - Requires understanding result calculation logic

**Cumulative**: Completing Tiers 4, 1, and 5 = **~5.8% gain → 73.8% total**
**Adding Tier 3**: **+2.5% → 76.3% total**
**Adding Tier 2**: **+3.7% → 80% GOAL ACHIEVED** 🎯

## Technical Notes

### Key Patterns for Success

1. **Use Existing Fixtures**: Leverage conftest.py fixtures (`admin_client`, `member_client`, `test_poll`, etc.)

2. **Model Creation**: Always include all required fields:
   ```python
   event = Event(
       name="Test Event",
       date=datetime.now().date(),
       year=datetime.now().year,  # Required!
       event_type="tournament",
   )

   lake = Lake(
       yaml_key="test-lake",  # Not 'name'
       display_name="Test Lake",  # This is the human-readable name
   )

   ramp = Ramp(
       lake_id=lake.id,
       name="Test Ramp",
       google_maps_iframe=None,  # Not 'coordinates'
   )
   ```

3. **Test Database Sessions**: Always refresh from DB after mutations:
   ```python
   db_session.expire_all()  # Refresh all objects from DB
   ```

4. **CSRF Handling**: Use `post_with_csrf()` helper for all POST requests

### Common Pitfalls to Avoid

❌ **Don't**: Create Event without `year` field
✅ **Do**: Always set `year=datetime.now().year`

❌ **Don't**: Use `Lake(name=..., location=...)`
✅ **Do**: Use `Lake(yaml_key=..., display_name=...)`

❌ **Don't**: Use `Ramp(coordinates=...)`
✅ **Do**: Use `Ramp(google_maps_iframe=...)`

❌ **Don't**: Create complex integration tests first
✅ **Do**: Start with simple unit tests for helpers

## Success Metrics

- **Code Coverage**: 80%+
- **Test Count**: 500+ tests passing
- **Test Speed**: < 3 minutes for full suite
- **Code Quality**: 100% (MyPy + Ruff clean)
- **No Regressions**: All existing tests pass

## Quick Start Commands

```bash
# Check current coverage
nix develop -c pytest --cov --cov-report=term

# Run specific test file
nix develop -c pytest tests/unit/test_new_helpers.py -v

# Check coverage for specific module
nix develop -c pytest --cov=core.helpers --cov-report=term

# Format and check before commit
nix develop -c format-code && nix develop -c check-code
```

## Conclusion

Reaching 80% coverage is achievable through systematic testing of the identified high-value targets. The roadmap prioritizes:

1. **Quick Wins** (helpers) for momentum
2. **High Value** (voting, pages) for impact
3. **Complex Features** (polls, tournaments) for completion

**Estimated Total Effort**: 19-26 hours
**Expected Outcome**: 80%+ coverage with robust test suite

---

**Status**: Ready for implementation
**Last Updated**: November 18, 2025
**Maintained By**: Development Team
