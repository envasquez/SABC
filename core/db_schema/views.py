"""SQL view definitions, shared between Alembic migrations and tests.

The Alembic migration ``k8l9m0n1o2p3_add_tournament_result_views.py`` creates
these views in production (PostgreSQL); the test suite imports the same SQL
to materialize them in SQLite after ``Base.metadata.create_all()``. Keeping
the DDL in one place avoids drift between the two environments.

See the migration's docstring for the design rationale (why two views, what
each one masks, what is intentionally out of scope).
"""

# Cross-dialect DDL: ``CAST(0 AS NUMERIC)`` works in both Postgres and SQLite,
# unlike the PG-only ``0::numeric`` shortcut.

ANGLER_TOURNAMENT_RESULTS_VIEW_SQL = """
CREATE VIEW v_angler_tournament_results AS
-- (1) Individual results row — source of truth whenever it exists.
SELECT
    r.tournament_id,
    r.angler_id,
    r.num_fish,
    r.total_weight,
    r.big_bass_weight,
    r.dead_fish_penalty,
    r.disqualified,
    r.buy_in,
    r.was_member,
    'results' AS source
FROM results r
JOIN anglers a ON a.id = r.angler_id
WHERE a.name != 'Admin User'

UNION ALL

-- (2) Team-format fallback for angler1 when no per-angler row exists.
SELECT
    tr.tournament_id,
    tr.angler1_id AS angler_id,
    tr.num_fish,
    tr.total_weight,
    tr.big_bass_weight,
    CAST(0 AS NUMERIC) AS dead_fish_penalty,
    FALSE AS disqualified,
    FALSE AS buy_in,
    TRUE AS was_member,
    'team_angler1' AS source
FROM team_results tr
JOIN anglers a1 ON a1.id = tr.angler1_id
WHERE NOT EXISTS (
    SELECT 1 FROM results r
    WHERE r.tournament_id = tr.tournament_id
      AND r.angler_id = tr.angler1_id
)
  AND a1.name != 'Admin User'

UNION ALL

-- (3) Angler2 fallback: zero stats to avoid double-counting the team total.
SELECT
    tr.tournament_id,
    tr.angler2_id AS angler_id,
    0 AS num_fish,
    CAST(0 AS NUMERIC) AS total_weight,
    CAST(0 AS NUMERIC) AS big_bass_weight,
    CAST(0 AS NUMERIC) AS dead_fish_penalty,
    FALSE AS disqualified,
    FALSE AS buy_in,
    TRUE AS was_member,
    'team_angler2' AS source
FROM team_results tr
JOIN anglers a2 ON a2.id = tr.angler2_id
WHERE tr.angler2_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM results r
    WHERE r.tournament_id = tr.tournament_id
      AND r.angler_id = tr.angler2_id
  )
  AND a2.name != 'Admin User'
"""

TEAM_TOURNAMENT_RESULTS_VIEW_SQL = """
CREATE VIEW v_team_tournament_results AS
-- (1) team_results is the canonical boat row when present.
SELECT
    tr.tournament_id,
    tr.angler1_id,
    tr.angler2_id,
    tr.num_fish,
    tr.total_weight,
    tr.big_bass_weight,
    tr.place_finish,
    'team_results' AS source
FROM team_results tr
JOIN anglers a1 ON a1.id = tr.angler1_id
LEFT JOIN anglers a2 ON a2.id = tr.angler2_id
WHERE a1.name != 'Admin User'
  AND (a2.id IS NULL OR a2.name != 'Admin User')

UNION ALL

-- (2) Individual results without a covering team_results row become a
--     "boat of one". place_finish is NULL — caller computes via ranking.
SELECT
    r.tournament_id,
    r.angler_id AS angler1_id,
    CAST(NULL AS INTEGER) AS angler2_id,
    r.num_fish,
    r.total_weight,
    r.big_bass_weight,
    CAST(NULL AS INTEGER) AS place_finish,
    'results' AS source
FROM results r
JOIN anglers a ON a.id = r.angler_id
WHERE a.name != 'Admin User'
  AND r.disqualified = FALSE
  AND r.buy_in = FALSE
  AND NOT EXISTS (
    SELECT 1 FROM team_results tr
    WHERE tr.tournament_id = r.tournament_id
      AND (tr.angler1_id = r.angler_id OR tr.angler2_id = r.angler_id)
  )
"""

ALL_VIEWS_SQL = (
    ANGLER_TOURNAMENT_RESULTS_VIEW_SQL,
    TEAM_TOURNAMENT_RESULTS_VIEW_SQL,
)

ALL_VIEW_DROP_SQL = (
    "DROP VIEW IF EXISTS v_team_tournament_results",
    "DROP VIEW IF EXISTS v_angler_tournament_results",
)
