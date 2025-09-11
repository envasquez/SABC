"""Database query helper functions to consolidate repeated patterns."""

from core.database import db


def get_tournament_stats(tournament_id, fish_limit):
    """Get comprehensive tournament statistics."""
    stats = db(
        """
        SELECT
            COUNT(DISTINCT r.angler_id) as total_anglers,
            SUM(r.num_fish) as total_fish,
            SUM(r.total_weight - r.dead_fish_penalty) as total_weight,
            COUNT(CASE WHEN r.num_fish = :fish_limit THEN 1 END) as limits,
            COUNT(CASE WHEN r.num_fish = 0 THEN 1 END) as zeros,
            COUNT(CASE WHEN r.buy_in = 1 THEN 1 END) as buy_ins,
            MAX(r.big_bass_weight) as big_bass,
            MAX(r.total_weight - r.dead_fish_penalty) as heavy_stringer
        FROM results r
        WHERE r.tournament_id = :tournament_id AND NOT r.disqualified
    """,
        {"tournament_id": tournament_id, "fish_limit": fish_limit},
    )
    return stats[0] if stats else [0] * 8


def get_individual_results(tournament_id, last_place_points):
    """Get individual tournament results with SABC scoring."""
    return db(
        """
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY
                    CASE WHEN r.num_fish > 0 THEN 0 ELSE 1 END,
                    (r.total_weight - r.dead_fish_penalty) DESC,
                    r.big_bass_weight DESC,
                    r.buy_in,
                    a.name
            ) as place,
            a.name,
            r.num_fish,
            r.total_weight - r.dead_fish_penalty as final_weight,
            r.big_bass_weight,
            CASE
                WHEN a.member = 0 THEN 0
                WHEN r.num_fish > 0 AND a.member = 1 THEN
                    100 - ROW_NUMBER() OVER (
                        PARTITION BY CASE WHEN r.num_fish > 0 AND a.member = 1 THEN 1 ELSE 0 END
                        ORDER BY (r.total_weight - r.dead_fish_penalty) DESC, r.big_bass_weight DESC
                    ) + 1
                WHEN r.buy_in = 1 AND a.member = 1 THEN :last_place_points - 4
                ELSE :last_place_points - 2
            END as points,
            r.dead_fish_penalty,
            r.buy_in,
            r.disqualified,
            a.member
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        ORDER BY place
    """,
        {"tournament_id": tournament_id, "last_place_points": last_place_points},
    )


def get_tournaments_with_results():
    """Get tournaments list with event and result data."""
    return db("""
        SELECT t.id, t.name, e.date, e.description,
               COUNT(DISTINCT r.angler_id) as participant_count,
               t.complete
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        LEFT JOIN results r ON t.id = r.tournament_id
        GROUP BY t.id, t.name, e.date, e.description, t.complete
        ORDER BY e.date DESC
    """)


def get_poll_options_with_votes(poll_id, include_details=False):
    """Get poll options with vote counts and optional voter details."""
    options_data = db(
        """
        SELECT po.id, po.option_text, po.option_data, COUNT(pv.id) as vote_count
        FROM poll_options po
        LEFT JOIN poll_votes pv ON po.id = pv.option_id
        WHERE po.poll_id = :poll_id
        GROUP BY po.id, po.option_text, po.option_data
        ORDER BY po.id
    """,
        {"poll_id": poll_id},
    )

    options = []
    for option_data in options_data:
        option_dict = {
            "id": option_data[0],
            "text": option_data[1],
            "data": option_data[2],
            "vote_count": option_data[3],
        }

        if include_details:
            vote_details = db(
                """
                SELECT pv.id, a.name, pv.created_at
                FROM poll_votes pv
                JOIN anglers a ON pv.angler_id = a.id
                WHERE pv.option_id = :option_id
                ORDER BY pv.created_at
            """,
                {"option_id": option_data[0]},
            )

            option_dict["votes"] = [
                {"vote_id": vote[0], "voter_name": vote[1], "voted_at": vote[2]}
                for vote in vote_details
            ]

        options.append(option_dict)

    return options
