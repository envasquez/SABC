def tournaments_count_query() -> str:
    return """SELECT COUNT(DISTINCT t.id) FROM results r
        JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id
        WHERE r.angler_id = :user_id AND r.disqualified = FALSE"""


def best_weight_query() -> str:
    return """SELECT COALESCE(MAX(r.total_weight - COALESCE(r.dead_fish_penalty, 0)), 0)
        FROM results r JOIN tournaments t ON r.tournament_id = t.id
        WHERE r.angler_id = :user_id AND r.disqualified = FALSE"""


def big_bass_query() -> str:
    return """SELECT COALESCE(MAX(r.big_bass_weight), 0) FROM results r
        JOIN tournaments t ON r.tournament_id = t.id
        WHERE r.angler_id = :user_id AND r.disqualified = FALSE"""


def current_finishes_query() -> str:
    return """SELECT SUM(CASE WHEN place = 1 THEN 1 ELSE 0 END) as first,
            SUM(CASE WHEN place = 2 THEN 1 ELSE 0 END) as second,
            SUM(CASE WHEN place = 3 THEN 1 ELSE 0 END) as third
        FROM (SELECT ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place
            FROM team_results tr JOIN tournaments t ON tr.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE (tr.angler1_id = :user_id OR tr.angler2_id = :user_id) AND e.year = :current_year
        ) AS current_year_results"""


def all_time_finishes_query() -> str:
    return """SELECT SUM(CASE WHEN place = 1 THEN 1 ELSE 0 END) as first,
            SUM(CASE WHEN place = 2 THEN 1 ELSE 0 END) as second,
            SUM(CASE WHEN place = 3 THEN 1 ELSE 0 END) as third
        FROM (SELECT ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place
            FROM team_results tr JOIN tournaments t ON tr.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE (tr.angler1_id = :user_id OR tr.angler2_id = :user_id) AND e.year >= 2022
        ) AS all_time_results"""


def aoy_position_query() -> str:
    return """WITH tournament_standings AS (
            SELECT r.angler_id, r.tournament_id, r.total_weight - COALESCE(r.dead_fish_penalty, 0) as adjusted_weight,
                r.num_fish, r.disqualified, r.buy_in,
                DENSE_RANK() OVER (PARTITION BY r.tournament_id ORDER BY
                    CASE WHEN r.disqualified = TRUE THEN 0 ELSE r.total_weight - COALESCE(r.dead_fish_penalty, 0) END DESC) as place_finish,
                COUNT(*) OVER (PARTITION BY r.tournament_id) as total_participants
            FROM results r JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id
            WHERE e.year = :current_year
        ), points_calc AS (
            SELECT angler_id, tournament_id, adjusted_weight, num_fish, place_finish,
                CASE WHEN disqualified = TRUE THEN 0 ELSE 101 - place_finish END as points
            FROM tournament_standings
        ), aoy_standings AS (
            SELECT a.id, a.name,
                SUM(CASE WHEN a.member = TRUE THEN pc.points ELSE 0 END) as total_points,
                SUM(pc.adjusted_weight) as total_weight,
                ROW_NUMBER() OVER (ORDER BY SUM(CASE WHEN a.member = TRUE THEN pc.points ELSE 0 END) DESC, SUM(pc.adjusted_weight) DESC) as position
            FROM anglers a JOIN points_calc pc ON a.id = pc.angler_id WHERE a.member = TRUE
            GROUP BY a.id, a.name
        ) SELECT position FROM aoy_standings WHERE id = :user_id"""
