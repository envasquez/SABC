# Testing Quick Start Guide

Quick reference for the CRUD test coverage initiative.

## 📋 The Plan

**Full Details**: [CRUD_TEST_COVERAGE_PLAN.md](CRUD_TEST_COVERAGE_PLAN.md)

**GitHub Tracking**: [Issue #189](https://github.com/envasquez/SABC/issues/189)

## 🎯 Current Status

- ✅ **Phase 0**: Complete (7 tournament poll tests)
- 🔜 **Phase 1**: Foreign Key Constraints (#184)
- ⏳ **Phase 2**: Data Validation (#185)
- ⏳ **Phase 3**: Authorization (#186)
- ⏳ **Phase 4**: Edge Cases & Security (#187)
- ⏳ **Phase 5**: Generic Poll Editing (#188)

## 🚀 Quick Commands

### Run All Tests
```bash
nix develop -c run-tests
```

### Run Specific Test File
```bash
nix develop -c pytest tests/integration/test_poll_edit_with_votes.py -v
```

### Run With Coverage
```bash
nix develop -c pytest --cov=. --cov-report=html
```

### Check Coverage Report
```bash
open htmlcov/index.html
```

## 📝 GitHub Issues

| Phase | Issue | Priority | Tests | Status |
|-------|-------|----------|-------|--------|
| Master | [#189](https://github.com/envasquez/SABC/issues/189) | - | - | 📋 Tracking |
| 1 | [#184](https://github.com/envasquez/SABC/issues/184) | P0 | 15-20 | 🔜 Next |
| 2 | [#185](https://github.com/envasquez/SABC/issues/185) | P1 | 20-25 | ⏳ Pending |
| 3 | [#186](https://github.com/envasquez/SABC/issues/186) | P1 | 15-20 | ⏳ Pending |
| 4 | [#187](https://github.com/envasquez/SABC/issues/187) | P2 | 15-20 | ⏳ Pending |
| 5 | [#188](https://github.com/envasquez/SABC/issues/188) | P1 | 7-10 | ⏳ Pending |

## 📊 Coverage Goals

| Metric | Current | Target |
|--------|---------|--------|
| Overall Coverage | 39.1% | >80% |
| CRUD Routes | ~25% | >90% |
| Test Count | 538 | ~620-650 |

## 🎓 Test Examples

### Tournament Poll Editing (Completed)
**File**: `tests/integration/test_poll_edit_with_votes.py`

This is the gold standard - comprehensive coverage including:
- Happy paths (polls without votes)
- Critical edge cases (polls with votes)
- Foreign key constraint handling
- Authorization checks

Use this as a template for other CRUD tests!

### Test Structure Pattern
```python
class TestEntityCRUD:
    """Test CRUD operations for Entity."""

    def test_create_happy_path(self, admin_client, db_session):
        """Test creating entity with valid data."""
        # Arrange
        form_data = {...}

        # Act
        response = post_with_csrf(admin_client, "/admin/entity/create", data=form_data)

        # Assert
        assert response.status_code in [200, 302, 303]
        entity = db_session.query(Entity).filter(...).first()
        assert entity is not None

    def test_create_with_invalid_data(self, admin_client):
        """Test creating entity with invalid data."""
        # Should reject and show error
        ...

    def test_delete_with_foreign_keys(self, admin_client, db_session):
        """Test deleting entity that has related records."""
        # Should prevent or cascade appropriately
        ...
```

## 🔥 Most Critical Gaps

Top 5 tests to write next (Phase 1):

1. **Delete event with poll votes** - Foreign key cascade chain
2. **Delete user with tournament results** - Data preservation
3. **Delete lake with poll options** - Reference integrity
4. **Edit generic poll options with votes** - Same bug as tournament polls
5. **Delete user with poll votes** - Foreign key handling

## 📚 Key Files

### Test Files
- `tests/integration/test_poll_edit_with_votes.py` - Example ✅
- `tests/integration/test_admin_crud_workflows.py` - Existing tests
- `tests/conftest.py` - Test fixtures and helpers

### Code Under Test
- `routes/admin/events/` - Event CRUD
- `routes/admin/polls/` - Poll CRUD
- `routes/admin/lakes/` - Lake/Ramp CRUD
- `routes/admin/users/` - User CRUD
- `routes/admin/tournaments/` - Result CRUD
- `routes/admin/core/news.py` - News CRUD

### Database
- `core/db_schema/models.py` - SQLAlchemy models
- `core/db_schema/` - Database schema

## 🛠️ Development Workflow

### Before Writing Tests
1. Read the relevant phase issue (#184, #185, etc.)
2. Review the plan: `docs/CRUD_TEST_COVERAGE_PLAN.md`
3. Look at example: `tests/integration/test_poll_edit_with_votes.py`
4. Check database schema for foreign keys

### Writing Tests
1. Create test file (or add to existing)
2. Follow the test structure pattern above
3. Write tests in order: happy path → validation → edge cases
4. Run tests frequently: `nix develop -c pytest <file> -v`

### After Writing Tests
1. Ensure all tests pass
2. Check coverage: `nix develop -c pytest --cov=.`
3. Format code: `nix develop -c format-code`
4. Type check: `nix develop -c check-code`
5. Commit with clear message
6. Update GitHub issue with progress

## 🎯 Success Checklist

For each CRUD operation, ensure tests for:

- [ ] ✅ Happy path - valid data succeeds
- [ ] ❌ Invalid data rejected with clear error
- [ ] ❌ Missing required fields rejected
- [ ] ❌ Foreign key constraints handled
- [ ] ❌ Authorization enforced (admin-only)
- [ ] ❌ Non-existent records return 404
- [ ] ❌ Duplicate data rejected (where applicable)
- [ ] ❌ Edge cases covered (empty strings, special chars, etc.)
- [ ] ❌ Security tests (XSS, injection prevention)

## 📞 Need Help?

- **Full Plan**: `docs/CRUD_TEST_COVERAGE_PLAN.md`
- **GitHub Issues**: https://github.com/envasquez/SABC/issues/189
- **Example Tests**: `tests/integration/test_poll_edit_with_votes.py`

---

**Last Updated**: 2025-11-18
**Next Review**: After Phase 1 completion
