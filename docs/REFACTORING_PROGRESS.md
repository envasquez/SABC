# Code Refactoring Progress

## Overview
Systematic refactoring to reduce code duplication from ~3,000+ lines across the codebase.

## Original Assessment
- **Grade**: B- (75/100)
- **Total Estimated Savings**: 3,000+ lines of code
- **Primary Issues**: Template duplication, generated JavaScript, inconsistent patterns

## Phases

### Phase 1: Quick Wins - Template Macros and Utilities ✅ PARTIALLY COMPLETE
**Goal**: 800-1,000 lines saved | **Actual**: 185 lines (23%) | **Status**: Stable & Merged

#### Completed ✅
- [x] Create `time_select_options()` macro - **PR #213**
- [x] Apply time_select_options to polls.html (**120 lines saved**) - **PR #214**
- [x] Create `seasonal_history_card()` macro - **PR #214**
- [x] Replace manual CSRF tokens with `csrf_token` macro (6 files) - **PR #215**
- [x] Create refactoring automation scripts (4 scripts)
- [x] All PRs merged (PRs #213, #214, #215)

#### Remaining (~600 lines available)
- [ ] Apply `seasonal_history_card` macro to polls.html (remaining duplicates, ~200-300 lines)
- [ ] Apply `delete_modal` macro across all templates (7 files, ~150-200 lines)
- [ ] Remove inline `getCsrfToken()` JavaScript implementations (7 files, ~60 lines)

**Current Savings**: **185 lines (12.7% reduction in polls.html)**
**Target**: 800-1,000 lines
**Completion**: 23%

---

### Phase 2: JavaScript Consolidation ⏳ PENDING
**Goal**: 200-300 lines saved | **Estimated Time**: 6-8 hours

**Tasks**:
- [ ] Add `showModal()` and `hideModal()` utilities to utils.js
- [ ] Refactor inline DELETE request handlers
- [ ] Create generic `deleteResource()` utility
- [ ] Extract admin-events filters to static/admin-events.js
- [ ] Remove all inline modal initialization code

**Issue**: #209

---

### Phase 3: Poll Voting Refactor (MAJOR IMPACT) ⏳ PENDING
**Goal**: 2,000+ lines saved | **Estimated Time**: 16-20 hours

**Problem**: polls.html generates ~265 lines of JavaScript per poll

**Solution**: Class-based `PollVotingHandler` approach

**Tasks**:
- [ ] Create static/polls.js with PollVotingHandler class
- [ ] Refactor templates/polls.html to use data attributes
- [ ] Remove all generated per-poll JavaScript functions
- [ ] Add comprehensive tests for poll voting
- [ ] Ensure voting works for all user types

**Target**: Reduce polls.html from 1,337 to ~600-700 lines

**Issue**: #210

---

### Phase 4: Backend Patterns Cleanup ⏳ PENDING
**Goal**: 150-200 lines saved | **Estimated Time**: 8-10 hours

**Tasks**:
- [ ] Create generic DELETE handler in core/helpers/crud.py
- [ ] Refactor all DELETE endpoints (9 files)
- [ ] Enforce response.py helper usage across all routes
- [ ] Add type hints to remaining functions

**Issue**: #211

---

### Phase 5: Component Library & Documentation ⏳ PENDING
**Goal**: Long-term maintainability | **Estimated Time**: 12-16 hours

**Tasks**:
- [ ] Create templates/components/ directory structure
- [ ] Document all components with usage examples
- [ ] Add pre-commit hook to check for pattern violations
- [ ] Create CONTRIBUTING.md with component usage guidelines

**Issue**: #212

---

## Progress Summary

| Phase | Status | Savings | Files Modified | PRs |
|-------|--------|---------|----------------|-----|
| Phase 1 | ✅ Partial (23%) | 185 / 800-1,000 | 10 | #213, #214, #215 |
| Phase 2 | ⏳ Pending | 0 / 200-300 | - | - |
| Phase 3 | ⏳ Pending | 0 / 2,000+ | - | - |
| Phase 4 | ⏳ Pending | 0 / 150-200 | - | - |
| Phase 5 | ⏳ Pending | 0 / Maintenance | - | - |
| **TOTAL** | **6%** | **185 / 3,000+** | **10** | **3** |

---

## Key Files by Duplication

| File | Original Lines | Current Lines | Target Lines | Reduction |
|------|---------------|---------------|--------------|-----------|
| templates/polls.html | 1,457 | 1,272 | ~600-700 | 185 / ~750 |
| templates/admin/events.html | 652 | 652 | ~450-500 | 0 / ~150 |
| templates/macros.html | 154 | 226 | Growing | +72 (good) |

---

## Testing Status

### Phase 1
- ✅ Code quality checks passing
- ✅ Type checking passing (0 mypy errors)
- ✅ Linting passing (0 ruff errors)
- ✅ All integration tests passing
- ✅ All PRs merged to master

---

## Notes

### Lessons Learned
1. **Automation helps**: Python script for regex replacements saved time
2. **Macros are powerful**: Single macro eliminates 40+ lines per use
3. **Start small**: 120 lines is good progress, builds momentum

### Risks
1. **Template changes**: Need thorough manual testing
2. **JavaScript refactor (Phase 3)**: Complex, high-risk, needs careful planning
3. **Breaking changes**: Must ensure backward compatibility

### Next Actions
1. Complete Phase 1 remaining tasks
2. Manual testing of polls.html time dropdowns
3. Get PR #213 reviewed and merged
4. Begin Phase 2 planning

---

**Last Updated**: 2025-11-24 (All Phase 1 PRs merged)
**Current Branch**: master
**Status**: Phase 1 partially complete (23%), ready for Phase 2 or Phase 3
**Next Steps**: Either complete Phase 1 remaining tasks (~600 lines) or move to Phase 3 (highest impact - 2,000+ lines)
