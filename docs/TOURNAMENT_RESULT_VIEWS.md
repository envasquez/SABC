# Tournament Result Views — Design + Reader-Migration Roadmap

This document covers two read-only SQL views introduced in migration
`k8l9m0n1o2p3_add_tournament_result_views.py` and the multi-phase plan to
migrate the ~30 reader sites that currently each implement their own
`results` + `team_results` reconciliation logic.

Created during the audit-driven Phase 10 refactor. The foundation (views +
test fixture) is in. **Reader migrations are still to do** — this doc tracks
which sites to migrate, in what order, and how to verify each.

## The problem these views solve

The codebase has two parallel result tables:

- **`results`** — per-angler row for a tournament. Source of truth for
  individual-format tournaments and for the per-angler stats inside
  team-format tournaments.
- **`team_results`** — per-team row for team-format tournaments. Carries
  the combined team total, big bass, and place. For individual-format
  tournaments these rows are sometimes present too (legacy).

Whether a tournament uses individual or team format is controlled by
**`Tournament.aoy_points`** (False = team format 2026+). The `Tournament.is_team`
column also exists but is mostly cosmetic (always True on insert) — code
reads `aoy_points` for the actual discriminator. Reconciling those two
flags is a separate cleanup, not blocked by these views.

The duality has caused a chain of ~20 fix commits (`87a43a3`, `1f36e90`,
`35fbbd1`, `cbea276`, `356e65e`, `97260ea`, `bb89eb7`, `44b8d35`, ...)
where readers each had to remember to consult both tables. Every new
feature on top of results is a chance to ship a regression.

## The views

### `v_angler_tournament_results`

One row per (tournament, angler), regardless of format. Columns mirror
`results`: `tournament_id, angler_id, num_fish, total_weight, big_bass_weight,
dead_fish_penalty, disqualified, buy_in, was_member, source`.

Population rules (in UNION-ALL order):

1. **`results` row** wins whenever present (source = `'results'`). This
   is the source of truth for individual-format tournaments and for any
   team-format tournament where the admin entered per-angler stats.
2. **team_results.angler1 fallback** when no `results` row exists for
   `angler1_id` (source = `'team_angler1'`). Carries the full team
   stats.
3. **team_results.angler2 fallback** when no `results` row exists for
   `angler2_id` (source = `'team_angler2'`). Zero stats so totals don't
   double-count, but the row exists so participation/count queries see it.

Always excludes the seed "Admin User" angler.

### `v_team_tournament_results`

One row per "boat" per tournament: `tournament_id, angler1_id, angler2_id,
num_fish, total_weight, big_bass_weight, place_finish, source`.

1. **team_results row** is canonical when present (source = `'team_results'`).
2. **Individual results synthesize a "boat of one"** (angler2_id = NULL)
   when no team_results row covers them (source = `'results'`).
   `disqualified` / `buy_in` rows are excluded — they'd skew rankings.

Excludes any boat with an Admin User on it.

## Reader-migration plan

The survey identified ~30 reader sites grouped into 4 strategies:

- **(A)** Reads only `results`, silently misses team-format tournaments.
  **These are bugs.** Highest-priority migrations.
- **(B)** Branches on `tournament.aoy_points` and joins both tables.
  Untested False branch; replace with single view query.
- **(C)** Queries only one table because data is format-specific. Lower
  priority — most are already correct; migrating to the view buys
  uniformity and the Admin User exclusion.
- **(D)** UNION-ALL of both tables with EXISTS guards / clever CASEs.
  Some have double-count bugs. High-priority for `data_queries.py`.

### Phase 11 — strategy (A) bug fixes (~9 sites)

These currently miss team-format data. Migrating fixes real bugs.

| File:line | What | View to use |
|---|---|---|
| `routes/pages/home.py:130-147` (`build_tournament_query`) | Homepage tile totals | `v_angler_tournament_results` for per-tournament SUM/COUNT |
| `routes/auth/profile.py:44-50` | Profile tournaments-count | `v_angler_tournament_results` COUNT(DISTINCT tournament_id) |
| `routes/auth/profile.py:54-60` | Profile best_weight | `v_angler_tournament_results` MAX(total_weight) |
| `routes/auth/profile.py:63-69` | Profile big_bass | `v_angler_tournament_results` MAX(big_bass_weight) |
| `routes/pages/awards_helpers.py:5-9` | `get_stats_query` yearly | `v_angler_tournament_results` |
| `routes/pages/awards_helpers.py:12-16` | `get_tournament_results_query` | `v_angler_tournament_results` |
| `routes/pages/awards_helpers.py:19-22` | Heavy stringer top10 | `v_angler_tournament_results` |
| `routes/pages/awards_helpers.py:25-28` | Big bass top10 | `v_angler_tournament_results` |
| `routes/voting/helpers.py:94-184` | `get_seasonal_tournament_history` | `v_angler_tournament_results` |
| `core/query_service/data_queries.py:314-334` | `get_big_bass_records` | `v_angler_tournament_results` |
| `routes/admin/core/event_queries.py:36` | `_has_results_column` past-events badge | `v_angler_tournament_results` |

**Verify each**: after migration, query the same data with a tournament
that has only `team_results` rows (use the new `test_team_format_tournament`
fixture) and confirm the result now includes that tournament.

### Phase 12 — strategy (D) consolidation (~6 sites in data_queries.py)

These have **double-count bugs** because they UNION both tables without
EXISTS guards:

- `core/query_service/data_queries.py:237-280` `get_lake_statistics`
- `core/query_service/data_queries.py:336-374` `get_membership_by_year`
- `core/query_service/data_queries.py:376-412` `get_weight_trends_by_year`
- `core/query_service/data_queries.py:414-460` `get_winning_weights_by_year`
- `core/query_service/data_queries.py:462-511` `get_winning_weights_by_lake`
- `core/query_service/data_queries.py:597-649` `get_winning_weights_by_lake_year`

⚠️ **Migrating these will change dashboard numbers visibly.** The new totals
are correct; the old ones double-counted team-format tournaments. Capture
current values on a representative dataset before migration, document the
delta in the commit.

The properly-guarded methods (`get_club_overview_stats`, `get_year_comparison_stats`,
`get_ytd_trends_by_year`, `get_limits_zeros_by_year`, `get_tournament_participation`)
will produce identical numbers after migration since they already do the
right thing — they just become simpler.

### Phase 13 — strategy (B) format-branchers (~4 sites)

- `routes/tournaments/data.py:53-76` (`calculate_big_bass_carryover`)
- `routes/tournaments/data.py:189-234` (header stats)
- `routes/tournaments/data.py:265-314` (big-bass winner)
- `core/query_service/tournament_queries.py:106-156` (`get_team_results` —
  replace with `v_team_tournament_results`)

Each branches on `tournament.aoy_points`. View-backed query is a single
SELECT and removes the per-format CASE/CASE WHEN logic.

### Phase 14 — strategy (C) cleanup (~8 sites)

These already work for their format-specific use case. Migrate for uniformity
+ the Admin User exclusion:

- `routes/pages/home.py:234-251` (`_fetch_top_results` podium) → `v_team_tournament_results`
- `routes/auth/profile.py:72-178` (team stats) → `v_team_tournament_results`
- `routes/pages/roster.py:56-186` (team stats) → `v_team_tournament_results`
- `routes/pages/awards_helpers.py:36-112` (team awards) → `v_team_tournament_results`
- `core/query_service/tournament_queries.py:31-50` (`get_tournament_results`) → `v_angler_tournament_results`

### Phase 15 — admin dashboard cleanup

- `routes/admin/core/dashboard_data.py:33-58` — `total_participants` =
  `result_count + team_result_count` is structurally wrong for team-format.
  Switch to `v_angler_tournament_results` COUNT.

### Phase 16 — cleanup

After all readers are migrated, delete:

- `routes/auth/profile_queries.py` (appears to be a dead duplicate — confirm by
  grep first; if any test references survive, those tests should be deleted too).
- Per-site Admin User filter (`a.name != 'Admin User'`) sprinkled across
  `tournament_queries.py`, `awards_helpers.py`, `data.py`, `roster.py`, `home.py`
  — the views handle this now.
- The two reconciliation flags: keep `Tournament.aoy_points` (it controls
  AOY points awarding, which still matters) but consider dropping `is_team`
  if no reader is left consulting it.

## Mutators (stay on raw tables)

These INSERT/UPDATE/DELETE the underlying tables and do **not** use the views:

- `routes/admin/tournaments/individual_results.py` (results CRUD)
- `routes/admin/tournaments/team_results.py` (team_results CRUD + place_finish recompute)
- `routes/admin/tournaments/manage_results.py` (cascading deletes)
- `core/services/account_merge.py` (UPDATEs both tables on angler merge)
- `scripts/audit_db_integrity.py`

## Test coverage gap to close

Until Phase 11 lands, every reader that branches on `aoy_points` has only
its True branch tested. The new `test_team_format_tournament` fixture
(`tests/conftest.py`) creates `aoy_points=False` tournaments. **Every
reader migration in Phase 11+ should add a test using that fixture** that
asserts the migrated query returns team-format data. Once Phase 11-14 are
done, audit reader tests for "Does this exercise both formats?" and add
the missing False-branch coverage.

## Verification commands

```bash
# Confirm both views were created
psql $DATABASE_URL -c "\dv v_*tournament*"

# Smoke-check a known tournament against both views
psql $DATABASE_URL -c "
  SELECT * FROM v_angler_tournament_results WHERE tournament_id = <ID>;
  SELECT * FROM v_team_tournament_results WHERE tournament_id = <ID>;
"
```
