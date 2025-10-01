from typing import Any, Dict, List


def calculate_tournament_points(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate tournament points for a list of results using SABC scoring system."""
    regular_results = [
        r for r in results if not r.get("buy_in", False) and not r.get("disqualified", False)
    ]
    fish_results = [r for r in regular_results if float(r.get("total_weight", 0)) > 0]
    zero_results = [r for r in regular_results if float(r.get("total_weight", 0)) == 0]
    fish_results.sort(key=lambda x: float(x.get("total_weight", 0)), reverse=True)
    current_place, current_points = 1, 100
    for i, result in enumerate(fish_results):
        weight = float(result.get("total_weight", 0))
        if i > 0:
            prev_weight = float(fish_results[i - 1].get("total_weight", 0))
            if weight != prev_weight:
                current_place = i + 1
                current_points = 100 - current_place + 1
        result["calculated_points"] = current_points
        result["calculated_place"] = current_place
    if fish_results:
        last_fish_points = min([r["calculated_points"] for r in fish_results])
        zero_points = last_fish_points - 2
        zero_place = len(fish_results) + 1
    else:
        zero_points = 98
        zero_place = 1
    for result in zero_results:
        result["calculated_points"] = zero_points
        result["calculated_place"] = zero_place
    return fish_results + zero_results


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
