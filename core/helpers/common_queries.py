from routes.dependencies import db


def get_officers():
    return db("""
        SELECT o.position, a.name, a.email, a.phone
        FROM officer_positions o
        JOIN anglers a ON o.angler_id = a.id
        WHERE o.year = 2025
        ORDER BY
            CASE o.position
                WHEN 'President' THEN 1
                WHEN 'Vice President' THEN 2
                WHEN 'Secretary' THEN 3
                WHEN 'Treasurer' THEN 4
                WHEN 'Weigh-master' THEN 5
                WHEN 'Assistant Weigh-master' THEN 6
                WHEN 'Technology Director' THEN 7
                ELSE 8
            END
    """)


def get_members_with_last_tournament():
    return db("""
        SELECT DISTINCT a.name, a.email, a.member, a.is_admin, a.created_at, a.phone,
               CASE
                   WHEN a.member = 0 THEN (
                       SELECT e.date
                       FROM results r
                       JOIN tournaments t ON r.tournament_id = t.id
                       JOIN events e ON t.event_id = e.id
                       WHERE r.angler_id = a.id
                       ORDER BY e.date DESC
                       LIMIT 1
                   )
                   ELSE NULL
               END as last_tournament_date
        FROM anglers a
        ORDER BY a.member DESC, a.name
    """)


def get_tournament_results(tournament_id):
    return db(
        """
        SELECT
            ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place,
            CASE
                WHEN tr.angler2_id IS NULL THEN a1.name
                ELSE a1.name || ' / ' || a2.name
            END as team_name,
            (SELECT SUM(num_fish) FROM results r WHERE r.angler_id IN (tr.angler1_id, tr.angler2_id) AND r.tournament_id = tr.tournament_id) as num_fish,
            tr.total_weight,
            a1.member as member1,
            a2.member as member2,
            tr.id as team_result_id,
            CASE WHEN tr.angler2_id IS NULL THEN 1 ELSE 0 END as is_solo
        FROM team_results tr
        JOIN anglers a1 ON tr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
        WHERE tr.tournament_id = :tournament_id
        AND NOT EXISTS (
            SELECT 1 FROM results r1
            WHERE r1.angler_id = tr.angler1_id
            AND r1.tournament_id = tr.tournament_id
            AND r1.buy_in = 1
        )
        AND (tr.angler2_id IS NULL OR NOT EXISTS (
            SELECT 1 FROM results r2
            WHERE r2.angler_id = tr.angler2_id
            AND r2.tournament_id = tr.tournament_id
            AND r2.buy_in = 1
        ))
        ORDER BY tr.total_weight DESC
    """,
        {"tournament_id": tournament_id},
    )


def get_individual_results(tournament_id):
    return db(
        """
        SELECT
            ROW_NUMBER() OVER (ORDER BY CASE WHEN r.num_fish > 0 THEN 0 ELSE 1 END, (r.total_weight - r.dead_fish_penalty) DESC, r.big_bass_weight DESC, r.buy_in, a.name) as place,
            a.name, r.num_fish, r.total_weight - r.dead_fish_penalty as final_weight, r.big_bass_weight,
            r.points, a.member,
            r.id as result_id
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        AND NOT r.disqualified
        AND r.buy_in = 0
        ORDER BY r.points DESC, (r.total_weight - r.dead_fish_penalty) DESC, r.big_bass_weight DESC, a.name
    """,
        {"tournament_id": tournament_id},
    )


def get_aoy_standings(year):
    return db(
        """
        SELECT
            a.name,
            SUM(r.points) as total_points,
            SUM(r.num_fish) as total_fish,
            SUM(r.total_weight - COALESCE(r.dead_fish_penalty, 0)) as total_weight,
            COUNT(DISTINCT r.tournament_id) as events_fished
        FROM anglers a
        JOIN results r ON a.id = r.angler_id
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        WHERE e.year = :year
        AND a.member = 1
        GROUP BY a.id, a.name
        ORDER BY total_points DESC, total_weight DESC
    """,
        {"year": year},
    )


def get_heavy_stringer(year):
    return db(
        """
        SELECT
            a.name,
            r.total_weight,
            r.num_fish,
            (substr(e.date, 1, 4) || ' ' ||
             CASE substr(e.date, 6, 2)
                 WHEN '01' THEN 'January'
                 WHEN '02' THEN 'February'
                 WHEN '03' THEN 'March'
                 WHEN '04' THEN 'April'
                 WHEN '05' THEN 'May'
                 WHEN '06' THEN 'June'
                 WHEN '07' THEN 'July'
                 WHEN '08' THEN 'August'
                 WHEN '09' THEN 'September'
                 WHEN '10' THEN 'October'
                 WHEN '11' THEN 'November'
                 WHEN '12' THEN 'December'
             END || ' Tournament') as tournament_name,
            e.date
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        WHERE e.year = :year AND r.total_weight > 0
        ORDER BY r.total_weight DESC
        LIMIT 1
    """,
        {"year": year},
    )


def get_big_bass(year):
    return db(
        """
        SELECT
            a.name,
            r.big_bass_weight,
            (substr(e.date, 1, 4) || ' ' ||
             CASE substr(e.date, 6, 2)
                 WHEN '01' THEN 'January'
                 WHEN '02' THEN 'February'
                 WHEN '03' THEN 'March'
                 WHEN '04' THEN 'April'
                 WHEN '05' THEN 'May'
                 WHEN '06' THEN 'June'
                 WHEN '07' THEN 'July'
                 WHEN '08' THEN 'August'
                 WHEN '09' THEN 'September'
                 WHEN '10' THEN 'October'
                 WHEN '11' THEN 'November'
                 WHEN '12' THEN 'December'
             END || ' Tournament') as tournament_name,
            e.date
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        WHERE e.year = :year AND r.big_bass_weight >= 5.0
        ORDER BY r.big_bass_weight DESC
        LIMIT 1
    """,
        {"year": year},
    )
