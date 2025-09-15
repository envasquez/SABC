from core.database import db


def get_tournament_stats(tournament_id, fish_limit):
    stats = db(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN r.buy_in = 0 THEN r.angler_id END) as total_anglers,
            SUM(r.num_fish) as total_fish,
            SUM(r.total_weight - r.dead_fish_penalty) as total_weight,
            COUNT(CASE WHEN r.num_fish = :fish_limit THEN 1 END) as limits,
            COUNT(CASE WHEN r.num_fish = 0 AND r.buy_in = 0 THEN 1 END) as zeros,
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
                SELECT pv.id, a.name, pv.voted_at
                FROM poll_votes pv
                JOIN anglers a ON pv.angler_id = a.id
                WHERE pv.option_id = :option_id
                ORDER BY pv.voted_at
            """,
                {"option_id": option_data[0]},
            )
            option_dict["votes"] = [
                {"vote_id": vote[0], "voter_name": vote[1], "voted_at": vote[2]}
                for vote in vote_details
            ]
        options.append(option_dict)

    return options


def get_lakes_list():
    lakes = db(
        "SELECT id, display_name, 'Central Texas' as location FROM lakes ORDER BY display_name"
    )
    return [(lake[0], lake[1], lake[2]) for lake in lakes]


def get_ramps_for_lake(lake_id):
    ramps = db(
        "SELECT id, name, lake_id FROM ramps WHERE lake_id = :lake_id ORDER BY name",
        {"lake_id": lake_id},
    )
    return [(str(ramp[0]), ramp[1], ramp[2]) for ramp in ramps]


def get_all_ramps():
    ramps = db("SELECT id, name, lake_id FROM ramps ORDER BY name")
    return [(ramp[0], ramp[1], ramp[2]) for ramp in ramps]


def find_lake_by_id(lake_id, return_format="full"):
    lake = db("SELECT id, display_name, yaml_key FROM lakes WHERE id = :id", {"id": lake_id})
    if not lake:
        return None if return_format == "name" else (None, None)

    if return_format == "name":
        return lake[0][1]

    lake_info = {"display_name": lake[0][1]}
    return lake[0][2], lake_info


def find_ramp_name_by_id(ramp_id):
    ramp = db("SELECT name FROM ramps WHERE id = :id", {"id": ramp_id})
    return ramp[0][0] if ramp else None


def validate_lake_ramp_combo(lake_id, ramp_id):
    ramp = db(
        "SELECT id FROM ramps WHERE id = :ramp_id AND lake_id = :lake_id",
        {"ramp_id": ramp_id, "lake_id": lake_id},
    )
    return bool(ramp)


def find_lake_data_by_db_name(db_lake_name):
    if not db_lake_name:
        return None, None, None

    lake = db(
        """
        SELECT yaml_key, display_name FROM lakes
        WHERE LOWER(display_name) = LOWER(:name) OR LOWER(yaml_key) = LOWER(:name)
    """,
        {"name": db_lake_name.strip()},
    )

    if lake:
        yaml_key, display_name = lake[0]
        lake_info = {"display_name": display_name}
        return yaml_key, lake_info, display_name
    lake = db(
        """
        SELECT yaml_key, display_name FROM lakes
        WHERE LOWER(display_name) LIKE '%' || LOWER(:name) || '%'
           OR LOWER(yaml_key) LIKE '%' || LOWER(:name) || '%'
        LIMIT 1
    """,
        {"name": db_lake_name.strip()},
    )
    if lake:
        yaml_key, display_name = lake[0]
        lake_info = {"display_name": display_name}
        return yaml_key, lake_info, display_name
    return None, None, None


def calculate_and_update_tournament_points(tournament_id):
    """
    Calculate and update points for all anglers in a tournament.

    SABC Scoring Rules:
    - Members with fish: 100 for 1st, 99 for 2nd, etc. (based on weight)
    - Guests: Always 0 points regardless of performance
    - Members with zero fish (no buy-in): 2 points less than last place member with fish
    - Members with buy-in: 4 points less than last place member with fish
    - Disqualified: 0 points
    """
    # First, get the count of MEMBERS with fish for calculating last place with fish points
    db(
        """
        SELECT COUNT(*)
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        AND r.num_fish > 0
        AND NOT r.disqualified
        AND r.buy_in = 0
        AND a.member = 1
    """,
        {"tournament_id": tournament_id},
    )[0][0]

    # Reset all points to 0 first
    db(
        "UPDATE results SET points = 0 WHERE tournament_id = :tournament_id",
        {"tournament_id": tournament_id},
    )

    # Update points for members with fish (non-buy-ins, non-disqualified)
    # First get the ranked results using DENSE_RANK for proper tie handling
    ranked_results = db(
        """
        SELECT
            r.id,
            DENSE_RANK() OVER (
                ORDER BY (r.total_weight - r.dead_fish_penalty) DESC,
                r.big_bass_weight DESC
            ) as rank
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        AND r.num_fish > 0
        AND NOT r.disqualified
        AND r.buy_in = 0
        AND a.member = 1
    """,
        {"tournament_id": tournament_id},
    )

    # Then update each result with its points
    for result_id, rank in ranked_results:
        db(
            "UPDATE results SET points = :points WHERE id = :result_id",
            {"points": 101 - rank, "result_id": result_id},
        )

    # Get the actual points of the last place finisher with fish for zero-fish calculations
    last_place_result = db(
        """
        SELECT points FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        AND r.num_fish > 0 AND NOT r.disqualified
        AND r.buy_in = 0 AND a.member = 1
        ORDER BY points ASC LIMIT 1
    """,
        {"tournament_id": tournament_id},
    )

    last_place_with_fish_points = last_place_result[0][0] if last_place_result else 100

    # Update points for members with zero fish (non-buy-ins)
    db(
        """
        UPDATE results
        SET points = :points
        FROM anglers a
        WHERE results.angler_id = a.id
        AND results.tournament_id = :tournament_id
        AND results.num_fish = 0
        AND results.buy_in = 0
        AND NOT results.disqualified
        AND a.member = 1
    """,
        {"tournament_id": tournament_id, "points": last_place_with_fish_points - 2},
    )

    # Update points for members with buy-ins
    db(
        """
        UPDATE results
        SET points = :points
        FROM anglers a
        WHERE results.angler_id = a.id
        AND results.tournament_id = :tournament_id
        AND results.buy_in = 1
        AND NOT results.disqualified
        AND a.member = 1
    """,
        {"tournament_id": tournament_id, "points": last_place_with_fish_points - 4},
    )

    # Guests and disqualified always get 0 points (already set by the reset)
    # but let's be explicit for clarity
    db(
        """
        UPDATE results
        SET points = 0
        FROM anglers a
        WHERE results.angler_id = a.id
        AND results.tournament_id = :tournament_id
        AND (a.member = 0 OR results.disqualified = 1)
    """,
        {"tournament_id": tournament_id},
    )

    return True
