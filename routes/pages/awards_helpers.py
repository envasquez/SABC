def get_years_query() -> str:
    return """SELECT DISTINCT year FROM events WHERE year IS NOT NULL AND year <= :year ORDER BY year DESC"""


def get_stats_query() -> str:
    return """SELECT COUNT(DISTINCT t.id) as total_tournaments, COUNT(DISTINCT a.id) as unique_anglers,
       SUM(r.num_fish) as total_fish, SUM(r.total_weight) as total_weight, AVG(r.total_weight) as avg_weight
       FROM tournaments t JOIN events e ON t.event_id = e.id JOIN results r ON t.id = r.tournament_id
       JOIN anglers a ON r.angler_id = a.id WHERE e.year = :year AND a.name != 'Admin User'"""


def get_tournament_results_query() -> str:
    return """SELECT t.id as tournament_id, a.id as angler_id, a.name as angler_name, r.total_weight, r.num_fish,
       r.big_bass_weight, r.buy_in, r.disqualified, r.was_member
       FROM results r JOIN anglers a ON r.angler_id = a.id JOIN tournaments t ON r.tournament_id = t.id
       JOIN events e ON t.event_id = e.id WHERE e.year = :year AND a.name != 'Admin User' ORDER BY t.id, r.total_weight DESC"""


def get_heavy_stringer_query() -> str:
    return """SELECT a.name, r.total_weight, r.num_fish, e.name as tournament_name, e.date FROM results r
       JOIN anglers a ON r.angler_id = a.id JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id
       WHERE e.year = :year AND r.total_weight > 0 AND a.name != 'Admin User' ORDER BY r.total_weight DESC LIMIT 10"""


def get_big_bass_query() -> str:
    return """SELECT a.name, r.big_bass_weight, e.name as tournament_name, e.date FROM results r
       JOIN anglers a ON r.angler_id = a.id JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id
       WHERE e.year = :year AND r.big_bass_weight >= 5.0 AND a.name != 'Admin User' ORDER BY r.big_bass_weight DESC LIMIT 10"""


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

    For 2026+ team format. Note: big_bass_weight is still tracked per individual result,
    but we join to team_results to get the team name.
    """
    return """
        SELECT
            CASE
                WHEN a1.name < a2.name THEN a1.name || ' & ' || a2.name
                WHEN a2.name IS NULL THEN a1.name
                ELSE a2.name || ' & ' || a1.name
            END as team_name,
            r.big_bass_weight,
            e.name as tournament_name,
            e.date
        FROM results r
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        JOIN team_results tr ON tr.tournament_id = t.id
            AND (tr.angler1_id = r.angler_id OR tr.angler2_id = r.angler_id)
        JOIN anglers a1 ON tr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
        WHERE e.year = :year
          AND r.big_bass_weight >= 5.0
          AND a1.name != 'Admin User'
        ORDER BY r.big_bass_weight DESC
        LIMIT 10
    """
