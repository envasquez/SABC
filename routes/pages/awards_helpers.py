def get_years_query() -> str:
    return """SELECT DISTINCT year FROM events WHERE year IS NOT NULL AND year <= :year ORDER BY year DESC"""


def get_stats_query() -> str:
    return """SELECT COUNT(DISTINCT t.id) as total_tournaments, COUNT(DISTINCT a.id) as unique_anglers,
       SUM(r.num_fish) as total_fish, SUM(r.total_weight) as total_weight, AVG(r.total_weight) as avg_weight
       FROM tournaments t JOIN events e ON t.event_id = e.id JOIN results r ON t.id = r.tournament_id
       JOIN anglers a ON r.angler_id = a.id WHERE e.year = :year AND a.name != 'Admin User'"""


def get_tournament_results_query() -> str:
    return """SELECT t.id as tournament_id, a.id as angler_id, a.name as angler_name, r.total_weight, r.num_fish, r.buy_in, r.disqualified
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
