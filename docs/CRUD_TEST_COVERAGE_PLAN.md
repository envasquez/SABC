# CRUD Test Coverage Plan

**Goal**: Ensure all CRUD operations are rock solid with comprehensive test coverage that prevents regressions and catches edge cases.

**Current Status**: Some CRUD operations tested, but gaps exist especially for edge cases and operations with foreign key constraints.

---

## Testing Strategy

### 1. Core Principles

Every CRUD operation must have tests for:

1. **Happy Path** - Normal operation succeeds
2. **Validation** - Invalid data rejected appropriately
3. **Authorization** - Only authorized users can perform operation
4. **Foreign Key Constraints** - Related data handled correctly
5. **Edge Cases** - Boundary conditions and unusual inputs
6. **Idempotency** - Where applicable, repeated operations are safe

### 2. Test Categories

#### A. Unit Tests
- **Purpose**: Test business logic in isolation
- **Scope**: Individual functions and methods
- **Coverage Target**: >90% for helper functions

#### B. Integration Tests
- **Purpose**: Test full request/response cycle
- **Scope**: HTTP endpoints with database
- **Coverage Target**: 100% of CRUD endpoints

#### C. Edge Case Tests
- **Purpose**: Test unusual conditions and error paths
- **Scope**: Foreign keys, race conditions, boundary values
- **Coverage Target**: All known edge cases documented

---

## CRUD Operations Inventory

### ✅ = Good Coverage | ⚠️ = Partial Coverage | ❌ = Missing Tests

### 1. Events (SABC Tournaments, Meetings)

**Routes**: `routes/admin/events/`

| Operation | Status | Existing Tests | Missing Tests |
|-----------|--------|----------------|---------------|
| **Create Event** | ⚠️ | Basic creation, with all fields | Validation failures, duplicate dates |
| **Update Event** | ⚠️ | Name, date, times, fee | With existing tournament data, foreign key impact |
| **Delete Event** | ⚠️ | Without results | With results, with polls, with votes, cascade behavior |
| **Validate Event** | ❌ | None | Date conflicts, required fields |

**Critical Edge Cases Needed**:
- [ ] Delete event with tournament results (should fail or cascade)
- [ ] Delete event with active poll (should fail or cascade)
- [ ] Delete event with poll votes (foreign key constraint)
- [ ] Update event date when tournament already entered
- [ ] Create event with invalid date range
- [ ] Create event with duplicate name/date

---

### 2. Polls (Generic & Tournament Location)

**Routes**: `routes/admin/polls/`

| Operation | Status | Existing Tests | Missing Tests |
|-----------|--------|----------------|---------------|
| **Create Generic Poll** | ⚠️ | Form access | Actual creation with options |
| **Create Tournament Poll** | ❌ | None | Creation with lake selections |
| **Edit Generic Poll** | ⚠️ | Title, dates | Options with votes, option deletion |
| **Edit Tournament Poll** | ✅ | Full coverage with votes | - |
| **Delete Poll** | ✅ | Basic deletion | - |

**Critical Edge Cases Needed**:
- [ ] Create poll with no options
- [ ] Create poll with duplicate options
- [ ] Edit generic poll options when votes exist
- [ ] Create poll with invalid date range (ends before starts)
- [ ] Create poll for non-existent event
- [ ] Edit poll to change type (generic <-> tournament)

---

### 3. Lakes & Ramps

**Routes**: `routes/admin/lakes/`

| Operation | Status | Existing Tests | Missing Tests |
|-----------|--------|----------------|---------------|
| **Create Lake** | ✅ | Basic creation | Duplicate yaml_key |
| **Update Lake** | ✅ | Display name | - |
| **Delete Lake** | ✅ | Basic deletion | With ramps, with poll options, with tournament history |
| **Create Ramp** | ✅ | Basic creation | Duplicate name for lake |
| **Update Ramp** | ✅ | Name change | - |
| **Delete Ramp** | ✅ | Basic deletion | With tournament results |

**Critical Edge Cases Needed**:
- [ ] Delete lake with active tournament poll options
- [ ] Delete lake with historical tournament results
- [ ] Delete ramp with tournament results
- [ ] Create ramp for non-existent lake
- [ ] Update lake yaml_key (should fail - referenced elsewhere)

---

### 4. Users/Anglers

**Routes**: `routes/admin/users/`

| Operation | Status | Existing Tests | Missing Tests |
|-----------|--------|----------------|---------------|
| **Create User** | ✅ | Basic creation | Duplicate email, invalid email |
| **Update User** | ⚠️ | Via edit route | Email change, member status change, admin promotion |
| **Delete User** | ✅ | Other users, self-prevention | With votes, with tournament results, with authored content |
| **Merge Accounts** | ❌ | None | Full merge workflow |

**Critical Edge Cases Needed**:
- [ ] Delete user with poll votes (foreign key)
- [ ] Delete user with tournament results (foreign key)
- [ ] Delete user who created polls/events
- [ ] Update user email to existing email (duplicate)
- [ ] Merge two users with conflicting data
- [ ] Demote last admin to non-admin (should fail)

---

### 5. News

**Routes**: `routes/admin/core/news.py`

| Operation | Status | Existing Tests | Missing Tests |
|-----------|--------|----------------|---------------|
| **Create News** | ✅ | Basic creation | XSS/injection attempts, empty content |
| **Update News** | ✅ | Content, priority | Published status change |
| **Delete News** | ✅ | Basic deletion | - |

**Critical Edge Cases Needed**:
- [ ] Create news with script tags (XSS prevention)
- [ ] Create news with very long content
- [ ] Update published news to unpublished
- [ ] Create news with future publish date

---

### 6. Tournament Results

**Routes**: `routes/admin/tournaments/`

| Operation | Status | Existing Tests | Missing Tests |
|-----------|--------|----------------|---------------|
| **Enter Individual Result** | ✅ | Basic entry, zero fish, DQ | Duplicate entry, negative weight |
| **Enter Team Result** | ✅ | Basic entry | Invalid team composition |
| **Delete Result** | ✅ | Basic deletion | Recalculation of points |
| **Manage Results** | ⚠️ | View page | Bulk operations |

**Critical Edge Cases Needed**:
- [ ] Enter result for non-existent tournament
- [ ] Enter result with negative weight
- [ ] Enter result with weight > 100 lbs (sanity check)
- [ ] Delete result and verify points recalculated
- [ ] Enter duplicate result for same angler/tournament
- [ ] Enter team result with same angler twice

---

## Testing Checklist Template

For each CRUD operation, ensure tests for:

### CREATE Operations
- [ ] ✅ Happy path - valid data creates record
- [ ] ✅ Returns appropriate success response/redirect
- [ ] ❌ Invalid data rejected with clear error message
- [ ] ❌ Duplicate data rejected (where applicable)
- [ ] ❌ Missing required fields rejected
- [ ] ❌ Foreign key violations handled (invalid references)
- [ ] ❌ Non-admin users blocked (authorization)
- [ ] ❌ XSS/injection attempts sanitized
- [ ] ❌ Boundary values (empty strings, very long strings, etc.)

### READ Operations
- [ ] ✅ Can retrieve existing records
- [ ] ✅ Returns 404 for non-existent records
- [ ] ✅ Proper pagination (if applicable)
- [ ] ❌ Access control enforced
- [ ] ❌ Proper handling of related data (joins)

### UPDATE Operations
- [ ] ✅ Happy path - valid changes applied
- [ ] ✅ Returns appropriate success response
- [ ] ❌ Invalid data rejected
- [ ] ❌ Non-existent record returns 404
- [ ] ❌ Foreign key constraints respected
- [ ] ❌ **Critical**: Updates with related data (votes, results, etc.)
- [ ] ❌ Partial updates work correctly
- [ ] ❌ Concurrent update handling (optimistic locking if used)
- [ ] ❌ Non-admin users blocked

### DELETE Operations
- [ ] ✅ Happy path - record deleted
- [ ] ✅ Returns appropriate success response
- [ ] ✅ Non-existent record handled gracefully
- [ ] ❌ **Critical**: Foreign key constraints (cascade vs prevent)
- [ ] ❌ Soft delete vs hard delete consistency
- [ ] ❌ Related data handled correctly
- [ ] ❌ Cannot delete if referenced by other records
- [ ] ❌ Non-admin users blocked
- [ ] ❌ Self-deletion prevention (for users)

---

## High-Priority Test Gaps

Based on the recent tournament poll editing bug, these are the highest priority gaps:

### Priority 1 (Critical) - Foreign Key Constraint Scenarios

1. **Delete Event with Poll Votes** ❌
   - Event → Poll → PollOption → PollVote chain
   - Should cascade or prevent deletion

2. **Delete User with Tournament Results** ❌
   - User has results in past tournaments
   - Should preserve results or prevent deletion

3. **Delete Lake with Poll Options** ❌
   - Lake referenced in active/past tournament polls
   - Should prevent deletion or cascade

4. **Edit Generic Poll Options with Votes** ❌
   - Similar to tournament poll issue we just fixed
   - May have same foreign key constraint issues

5. **Delete User with Poll Votes** ❌
   - User has voted in polls
   - Should preserve votes or prevent deletion

### Priority 2 (High) - Validation & Data Integrity

6. **Event Date Validation** ❌
   - Creating events with past dates
   - Creating events with end before start
   - Duplicate events on same date

7. **Poll Option Validation** ❌
   - Creating polls with 0 options
   - Creating polls with duplicate options
   - Max number of options

8. **Result Weight Validation** ❌
   - Negative weights
   - Unrealistic weights (>100 lbs)
   - Non-numeric inputs

9. **User Email Uniqueness** ❌
   - Creating user with existing email
   - Updating user to existing email

### Priority 3 (Medium) - Authorization & Security

10. **Non-Admin CRUD Attempts** ⚠️
    - Partially covered, need comprehensive coverage
    - All CREATE/UPDATE/DELETE should be admin-only

11. **XSS Prevention** ❌
    - Script tags in news content
    - Script tags in event descriptions
    - Script tags in poll options

12. **SQL Injection Prevention** ❌
    - Malicious input in search/filter fields
    - Special characters in text fields

---

## Implementation Plan

### Phase 1: Critical Foreign Key Tests (Week 1)
**Goal**: Prevent foreign key violation errors like tournament poll bug

1. Create `tests/integration/test_foreign_key_constraints.py`
2. Test all delete operations with related data
3. Test all update operations that affect related records
4. Document cascade vs prevent behavior

**Estimated**: 15-20 new tests

### Phase 2: Validation Tests (Week 2)
**Goal**: Ensure data integrity and clear error messages

1. Create `tests/integration/test_crud_validation.py`
2. Test all required field validations
3. Test all data type validations
4. Test all business rule validations (dates, duplicates, etc.)

**Estimated**: 20-25 new tests

### Phase 3: Authorization Tests (Week 3)
**Goal**: Ensure proper access control

1. Create `tests/integration/test_crud_authorization.py`
2. Test admin-only operations blocked for members
3. Test member-only operations blocked for anonymous users
4. Test self-modification restrictions

**Estimated**: 15-20 new tests

### Phase 4: Edge Cases & Security (Week 4)
**Goal**: Handle unusual inputs and prevent attacks

1. Create `tests/integration/test_crud_edge_cases.py`
2. Create `tests/integration/test_crud_security.py`
3. Test boundary values, empty inputs, very long inputs
4. Test XSS prevention, injection prevention

**Estimated**: 15-20 new tests

### Phase 5: Generic Poll Editing (Week 5)
**Goal**: Same level of coverage as tournament polls

1. Create `tests/integration/test_generic_poll_edit_with_votes.py`
2. Mirror tournament poll test structure
3. Test option add/remove with votes

**Estimated**: 7-10 new tests

---

## Success Metrics

### Coverage Goals
- **Integration Test Coverage**: 100% of all CRUD endpoints
- **Edge Case Coverage**: 100% of known edge cases documented and tested
- **Code Coverage**: >80% overall, >90% for CRUD routes

### Quality Goals
- **Zero Foreign Key Violations**: All constraint scenarios tested
- **Clear Error Messages**: All error paths return helpful messages
- **Fast Tests**: Full CRUD test suite runs in <60 seconds
- **Maintainable**: Tests are clear, well-documented, follow patterns

### Regression Prevention
- **Bug Prevention**: All reported bugs have regression tests
- **Documentation**: Each test has clear docstring explaining scenario
- **CI/CD Integration**: All tests run on every commit

---

## Test Organization

```
tests/
├── integration/
│   ├── test_admin_crud_workflows.py          # Existing - basic CRUD
│   ├── test_poll_edit_with_votes.py           # New - tournament polls ✅
│   ├── test_foreign_key_constraints.py        # Phase 1 - FK scenarios
│   ├── test_crud_validation.py                # Phase 2 - validation
│   ├── test_crud_authorization.py             # Phase 3 - access control
│   ├── test_crud_edge_cases.py                # Phase 4 - edge cases
│   ├── test_crud_security.py                  # Phase 4 - XSS, injection
│   └── test_generic_poll_edit_with_votes.py   # Phase 5 - generic polls
└── unit/
    ├── test_validation_helpers.py             # Validation logic
    ├── test_sanitization.py                   # XSS prevention
    └── test_authorization_helpers.py          # Auth logic
```

---

## Tracking & Reporting

### GitHub Issues
Create issues for each phase with:
- Checklist of tests to implement
- Acceptance criteria (all tests passing)
- Link to this plan
- Estimated effort
- Priority label

### Progress Dashboard
Track in GitHub Projects:
- Column 1: Backlog (not started)
- Column 2: In Progress (being written)
- Column 3: In Review (PR open)
- Column 4: Done (merged)

### Weekly Status
Report each Friday:
- Tests written this week
- Coverage percentage increase
- Bugs found during testing
- Blockers or concerns

---

## Long-Term Maintenance

### New Feature Checklist
When adding new CRUD operations:
- [ ] Write tests BEFORE implementing feature (TDD)
- [ ] Follow test checklist template above
- [ ] Add foreign key constraint tests
- [ ] Add validation tests
- [ ] Add authorization tests
- [ ] Update this document with new operations

### Quarterly Review
Every 3 months:
- Review test coverage metrics
- Identify new edge cases from production logs
- Update this plan with lessons learned
- Archive obsolete tests

---

## Resources & References

- **Existing Tests**: `tests/integration/test_admin_crud_workflows.py`
- **Tournament Poll Tests**: `tests/integration/test_poll_edit_with_votes.py` (example of comprehensive coverage)
- **Database Schema**: `core/db_schema/models.py`
- **Foreign Key Documentation**: `docs/DATABASE_MIGRATIONS.md`

---

## Questions & Decisions

### Open Questions
1. Should we use soft deletes for any entities? (preserve data vs clean database)
2. What's the cascade strategy for each foreign key? (cascade vs prevent)
3. Do we need optimistic locking for concurrent updates?
4. Should we test performance/load scenarios for CRUD operations?

### Decisions Made
1. ✅ Tournament poll editing uses smart update strategy (keep voted options)
2. ✅ All CRUD operations require admin authentication
3. ✅ XSS prevention via sanitization helpers

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Owner**: Development Team
**Review Cycle**: Monthly
