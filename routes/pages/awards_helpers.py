from core.helpers.members import exclude_seed_admin_sql


def get_years_query() -> str:
    return """SELECT DISTINCT year FROM events WHERE year IS NOT NULL AND year <= :year ORDER BY year DESC"""


def get_stats_query() -> str:
    """Yearly aggregates over the unified per-angler view, so team-format
    (aoy_points=False) tournaments contribute to the year's stats. The
    Admin User exclusion lives in the view definition."""
    return """SELECT COUNT(DISTINCT t.id) as total_tournaments, COUNT(DISTINCT vatr.angler_id) as unique_anglers,
       SUM(vatr.num_fish) as total_fish, SUM(vatr.total_weight) as total_weight, AVG(vatr.total_weight) as avg_weight
       FROM tournaments t JOIN events e ON t.event_id = e.id
       JOIN v_angler_tournament_results vatr ON t.id = vatr.tournament_id
       WHERE e.year = :year"""


def get_tournament_results_query() -> str:
    return """SELECT t.id as tournament_id, a.id as angler_id, a.name as angler_name, vatr.total_weight, vatr.num_fish,
       vatr.big_bass_weight, vatr.buy_in, vatr.disqualified, vatr.was_member
       FROM v_angler_tournament_results vatr JOIN anglers a ON vatr.angler_id = a.id
       JOIN tournaments t ON vatr.tournament_id = t.id
       JOIN events e ON t.event_id = e.id WHERE e.year = :year ORDER BY t.id, vatr.total_weight DESC"""


def get_heavy_stringer_query() -> str:
    return """SELECT a.name, vatr.total_weight, vatr.num_fish, e.name as tournament_name, e.date
       FROM v_angler_tournament_results vatr JOIN anglers a ON vatr.angler_id = a.id
       JOIN tournaments t ON vatr.tournament_id = t.id JOIN events e ON t.event_id = e.id
       WHERE e.year = :year AND vatr.total_weight > 0 ORDER BY vatr.total_weight DESC LIMIT 10"""


def get_big_bass_query() -> str:
    return """SELECT a.name, vatr.big_bass_weight, e.name as tournament_name, e.date
       FROM v_angler_tournament_results vatr JOIN anglers a ON vatr.angler_id = a.id
       JOIN tournaments t ON vatr.tournament_id = t.id JOIN events e ON t.event_id = e.id
       WHERE e.year = :year AND vatr.big_bass_weight >= 5.0 ORDER BY vatr.big_bass_weight DESC LIMIT 10"""


def get_team_heavy_stringer_query() -> str:
    """Teams ranked by heaviest single tournament weight for the year."""
    return """
        SELECT
            CASE
                WHEN a1.name < a2.name THEN a1.name || ' & ' || a2.name
                WHEN a2.name IS NULL THEN a1.name
                ELSE a2.name || ' & ' || a1.name
            END as team_name,
            vttr.total_weight,
            e.name as tournament_name,
            e.date
        FROM v_team_tournament_results vttr
        JOIN tournaments t ON vttr.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        JOIN anglers a1 ON vttr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON vttr.angler2_id = a2.id
        WHERE vttr.source = 'team_results'
          AND e.year = :year
          AND vttr.total_weight > 0
        ORDER BY vttr.total_weight DESC
        LIMIT 10
    """


def get_team_big_bass_query() -> str:
    """Teams with biggest bass for the year (team format)."""
    return """
        SELECT
            CASE
                WHEN a1.name < a2.name THEN a1.name || ' & ' || a2.name
                WHEN a2.name IS NULL THEN a1.name
                ELSE a2.name || ' & ' || a1.name
            END as team_name,
            vttr.big_bass_weight,
            e.name as tournament_name,
            e.date
        FROM v_team_tournament_results vttr
        JOIN tournaments t ON vttr.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        JOIN anglers a1 ON vttr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON vttr.angler2_id = a2.id
        WHERE vttr.source = 'team_results'
          AND e.year = :year
          AND vttr.big_bass_weight >= 5.0
        ORDER BY vttr.big_bass_weight DESC
        LIMIT 10
    """


# ---------------------------------------------------------------------------
# 2026+ season leaderboards
#
# Every board below is derived from ONE scan of v_team_tournament_results, at
# two grains: per angler (each angler credited with the boat they fished) and
# per exact boat pairing. One query per grain returns every metric, and the
# route slices/sorts it in Python for each individual board -- sorting ten
# rows is cheaper than ten GROUP BY round-trips, and it keeps the ranking
# tiebreakers in one place.
#
# `source = 'team_results'` matches the pre-existing team queries above: the
# view also synthesizes boats-of-one from individual results, which must not
# appear as "teams" on a team-format awards page.
# ---------------------------------------------------------------------------

#: SQL expression yielding a stable identity for a boat pairing, independent
#: of which angler happens to be angler1. Used to join computed earnings onto
#: the aggregates below. CAST(... AS TEXT) and || are portable across both
#: PostgreSQL and SQLite.
TEAM_KEY_SQL = """
            CASE
                WHEN vttr.angler2_id IS NULL THEN CAST(vttr.angler1_id AS TEXT)
                WHEN vttr.angler1_id < vttr.angler2_id
                    THEN CAST(vttr.angler1_id AS TEXT) || '-' || CAST(vttr.angler2_id AS TEXT)
                ELSE CAST(vttr.angler2_id AS TEXT) || '-' || CAST(vttr.angler1_id AS TEXT)
            END"""

#: Display name for a boat pairing: both names, alphabetical, or the single
#: name for a solo boat. Mirrors the expression used by the team queries above.
TEAM_NAME_SQL = """
            CASE
                WHEN a2.name IS NULL THEN a1.name
                WHEN a1.name < a2.name THEN a1.name || ' & ' || a2.name
                ELSE a2.name || ' & ' || a1.name
            END"""


def get_angler_season_stats_query() -> str:
    """Per-angler season totals across the year's team-format tournaments.

    Each angler is credited with their boat's finish, fish and weight for
    every event they fished: a shared bag cannot be split between the two
    anglers in it, so both are credited the boat total. (Money is the one
    metric that IS divisible, and it is split 50/50 in ``awards_money``.)

    Restricted to anglers flagged ``member``, matching the AOY standings
    filter the individual-format page already applies -- awards go to
    members. The dues check deliberately does NOT apply: dues lapse after a
    season ends, and that must not retroactively erase a season's awards.

    The seed admin is excluded explicitly: the views' own exclusion is keyed
    on the display name, which matches nothing in production.
    """
    return f"""
        WITH boats AS (
            SELECT vttr.tournament_id, vttr.angler1_id, vttr.angler2_id,
                   vttr.num_fish, vttr.total_weight, vttr.big_bass_weight,
                   vttr.place_finish
            FROM v_team_tournament_results vttr
            JOIN tournaments t ON vttr.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE vttr.source = 'team_results' AND e.year = :year
        ),
        boat_anglers AS (
            SELECT tournament_id, angler1_id AS angler_id, num_fish,
                   total_weight, big_bass_weight, place_finish
            FROM boats
            UNION ALL
            SELECT tournament_id, angler2_id AS angler_id, num_fish,
                   total_weight, big_bass_weight, place_finish
            FROM boats
            WHERE angler2_id IS NOT NULL
        )
        SELECT a.id AS angler_id,
               a.name,
               COUNT(*) AS events,
               SUM(CASE WHEN ba.place_finish = 1 THEN 1 ELSE 0 END) AS firsts,
               SUM(CASE WHEN ba.place_finish = 2 THEN 1 ELSE 0 END) AS seconds,
               SUM(CASE WHEN ba.place_finish = 3 THEN 1 ELSE 0 END) AS thirds,
               SUM(CASE WHEN ba.place_finish BETWEEN 1 AND 3 THEN 1 ELSE 0 END) AS top3,
               COALESCE(SUM(ba.num_fish), 0) AS total_fish,
               COALESCE(SUM(ba.total_weight), 0) AS total_weight,
               COALESCE(MAX(ba.total_weight), 0) AS best_stringer,
               COALESCE(MAX(ba.big_bass_weight), 0) AS best_bass
        FROM boat_anglers ba
        JOIN anglers a ON a.id = ba.angler_id
        WHERE a.member = TRUE AND {exclude_seed_admin_sql("a")}
        GROUP BY a.id, a.name
    """


def get_team_season_stats_query() -> str:
    """Per-pairing season totals across the year's team-format tournaments.

    Same metrics as :func:`get_angler_season_stats_query` but grouped by the
    exact boat. Note that partners re-pair between events, so most pairings
    will show a single event -- this grain answers "which boat did best
    together", not "who had the best season".

    No ``member`` filter: a boat qualifies on having at least one member,
    and that member's guest partner should not make the boat vanish.
    """
    a1_excluded = exclude_seed_admin_sql("a1")
    a2_excluded = exclude_seed_admin_sql("a2")
    return f"""
        SELECT {TEAM_KEY_SQL} AS team_key,
               {TEAM_NAME_SQL} AS team_name,
               COUNT(*) AS events,
               SUM(CASE WHEN vttr.place_finish = 1 THEN 1 ELSE 0 END) AS firsts,
               SUM(CASE WHEN vttr.place_finish = 2 THEN 1 ELSE 0 END) AS seconds,
               SUM(CASE WHEN vttr.place_finish = 3 THEN 1 ELSE 0 END) AS thirds,
               SUM(CASE WHEN vttr.place_finish BETWEEN 1 AND 3 THEN 1 ELSE 0 END) AS top3,
               COALESCE(SUM(vttr.num_fish), 0) AS total_fish,
               COALESCE(SUM(vttr.total_weight), 0) AS total_weight,
               COALESCE(MAX(vttr.total_weight), 0) AS best_stringer,
               COALESCE(MAX(vttr.big_bass_weight), 0) AS best_bass
        FROM v_team_tournament_results vttr
        JOIN tournaments t ON vttr.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        JOIN anglers a1 ON vttr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON vttr.angler2_id = a2.id
        WHERE vttr.source = 'team_results'
          AND e.year = :year
          AND {a1_excluded}
          AND (a2.id IS NULL OR {a2_excluded})
        GROUP BY {TEAM_KEY_SQL}, {TEAM_NAME_SQL}
    """
