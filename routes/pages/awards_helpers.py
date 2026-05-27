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


def get_team_wins_query() -> str:
    """Get teams ranked by number of 1st place finishes for the year.

    For 2026+ team format, tracks which team combinations have the most wins.
    """
    return """
        SELECT
            CASE
                WHEN a1.name < a2.name THEN a1.name || ' & ' || a2.name
                WHEN a2.name IS NULL THEN a1.name
                ELSE a2.name || ' & ' || a1.name
            END as team_name,
            COUNT(*) as wins,
            COUNT(DISTINCT tr.tournament_id) as tournaments_fished
        FROM team_results tr
        JOIN tournaments t ON tr.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        JOIN anglers a1 ON tr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
        WHERE e.year = :year
          AND tr.place_finish = 1
          AND a1.name != 'Admin User'
        GROUP BY team_name
        ORDER BY wins DESC, team_name
        LIMIT 10
    """


def get_team_heavy_stringer_query() -> str:
    """Get teams ranked by heaviest single tournament weight for the year.

    For 2026+ team format, returns team-based heavy stringer results.
    """
    return """
        SELECT
            CASE
                WHEN a1.name < a2.name THEN a1.name || ' & ' || a2.name
                WHEN a2.name IS NULL THEN a1.name
                ELSE a2.name || ' & ' || a1.name
            END as team_name,
            tr.total_weight,
            e.name as tournament_name,
            e.date
        FROM team_results tr
        JOIN tournaments t ON tr.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        JOIN anglers a1 ON tr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
        WHERE e.year = :year
          AND tr.total_weight > 0
          AND a1.name != 'Admin User'
        ORDER BY tr.total_weight DESC
        LIMIT 10
    """


def get_team_big_bass_query() -> str:
    """Get teams with biggest bass for the year.

    For 2026+ team format, big_bass_weight is stored directly in team_results.
    """
    return """
        SELECT
            CASE
                WHEN a1.name < a2.name THEN a1.name || ' & ' || a2.name
                WHEN a2.name IS NULL THEN a1.name
                ELSE a2.name || ' & ' || a1.name
            END as team_name,
            tr.big_bass_weight,
            e.name as tournament_name,
            e.date
        FROM team_results tr
        JOIN tournaments t ON tr.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        JOIN anglers a1 ON tr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
        WHERE e.year = :year
          AND tr.big_bass_weight >= 5.0
          AND a1.name != 'Admin User'
        ORDER BY tr.big_bass_weight DESC
        LIMIT 10
    """
