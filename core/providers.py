from datetime import datetime

from fastapi import Depends

from core.db_schema import engine
from core.helpers.auth import get_user_optional
from core.query_service import QueryService


async def get_tournament_data(tournament_id: int, user=Depends(get_user_optional)):
    try:
        with engine.connect() as conn:
            qs = QueryService(conn)

            tournament = qs.fetch_one(
                """SELECT t.id, t.event_id, e.date, e.name, e.description,
                   t.lake_name, t.ramp_name, t.entry_fee, t.fish_limit,
                   t.complete, e.event_type
                   FROM tournaments t JOIN events e ON t.event_id = e.id
                   WHERE t.id = :tournament_id""",
                {"tournament_id": tournament_id},
            )

            if not tournament:
                return None

            # Convert tournament dict to tuple for template compatibility
            tournament_tuple = (
                tournament["id"],                # 0
                tournament["event_id"],          # 1
                tournament["date"],              # 2
                tournament["name"],              # 3
                tournament["description"],       # 4
                tournament["lake_name"],         # 5
                tournament["ramp_name"],         # 6
                tournament["entry_fee"],         # 7
                tournament["fish_limit"],        # 8
                tournament["complete"],          # 9
                tournament["event_type"]         # 10
            )

            # Get tournament statistics in the format expected by template
            stats_query = qs.fetch_one(
                """SELECT
                   COUNT(DISTINCT CASE WHEN r.buy_in = FALSE THEN r.angler_id END) as total_anglers,                    -- 0: Anglers (exclude buy-ins)
                   SUM(CASE WHEN r.buy_in = FALSE THEN r.num_fish ELSE 0 END) as total_fish,                           -- 1: Total Fish (exclude buy-ins)
                   SUM(CASE WHEN r.buy_in = FALSE THEN r.total_weight ELSE 0 END) as total_weight,                     -- 2: Total Weight (exclude buy-ins)
                   COUNT(CASE WHEN r.buy_in = FALSE AND r.num_fish >= :fish_limit THEN 1 END) as limits,              -- 3: Limits (exclude buy-ins)
                   COUNT(CASE WHEN r.buy_in = FALSE AND r.num_fish = 0 THEN 1 END) as zeros,                          -- 4: Zeros (exclude buy-ins)
                   COUNT(CASE WHEN r.buy_in = TRUE THEN 1 END) as buy_ins,                                             -- 5: Buy-ins
                   MAX(CASE WHEN r.buy_in = FALSE THEN r.big_bass_weight END) as biggest_bass,                         -- 6: Big Bass (exclude buy-ins)
                   MAX(CASE WHEN r.buy_in = FALSE THEN r.total_weight END) as heavy_stringer                           -- 7: Heavy Stringer (exclude buy-ins)
                   FROM results r WHERE r.tournament_id = :id""",
                {"id": tournament_id, "fish_limit": tournament_tuple[8] or 5},
            )

            # Convert to tuple format for template
            stats = (
                stats_query["total_anglers"] or 0,
                stats_query["total_fish"] or 0,
                float(stats_query["total_weight"] or 0),
                stats_query["limits"] or 0,
                stats_query["zeros"] or 0,
                stats_query["buy_ins"] or 0,
                float(stats_query["biggest_bass"] or 0),
                float(stats_query["heavy_stringer"] or 0)
            ) if stats_query else (0, 0, 0.0, 0, 0, 0, 0.0, 0.0)

            # Get team results and convert to tuple format for template
            team_results_raw = qs.get_team_results(tournament_id)
            team_results = []
            for result in team_results_raw:
                # Convert to tuple format expected by template
                team_tuple = (
                    result.get("place_finish", 0),           # 0: place
                    f"{result.get('angler1_name', '')} / {result.get('angler2_name', '')}", # 1: team name
                    0,  # 2: fish count (not used for teams typically)
                    float(result.get("total_weight", 0)),    # 3: weight
                    0,  # 4: member status angler 1 (simplified)
                    0,  # 5: member status angler 2 (simplified)
                    result.get("id", 0),                     # 6: team result id
                    2   # 7: team size indicator
                )
                team_results.append(team_tuple)

            # Get individual results and convert to tuple format for template
            individual_results_raw = qs.get_tournament_results(tournament_id)
            individual_results = []

            # Filter out buy-ins and disqualified anglers for regular place calculation
            regular_results = [r for r in individual_results_raw if not r.get("buy_in", False) and not r.get("disqualified", False)]

            # Separate results into fish vs no-fish for proper SABC scoring
            fish_results = [r for r in regular_results if float(r.get("total_weight", 0)) > 0]
            zero_results = [r for r in regular_results if float(r.get("total_weight", 0)) == 0]

            # Calculate places and points for participants with fish
            current_place = 1
            for i, result in enumerate(fish_results):
                weight = float(result.get("total_weight", 0))

                # If this weight is different from previous, update place
                if i > 0:
                    prev_weight = float(fish_results[i-1].get("total_weight", 0))
                    if weight != prev_weight:
                        current_place = i + 1

                # Calculate points using SABC system: 101 - place
                points = max(101 - current_place, 0)

                result_tuple = (
                    current_place,                      # 0: place
                    result.get("angler_name", ""),      # 1: name
                    result.get("num_fish", 0),          # 2: fish count
                    weight,                             # 3: weight
                    float(result.get("big_bass_weight", 0)), # 4: big bass
                    points,                             # 5: points
                    result.get("member", 1),            # 6: member status
                    result.get("id", 0)                 # 7: result id
                )
                individual_results.append(result_tuple)

            # Calculate points for zero-fish participants per bylaws
            # They get 2 points less than last place participant that weighed in fish
            if fish_results:
                last_fish_points = min([t[5] for t in individual_results])  # Lowest points from fish results
                zero_points = last_fish_points - 2  # Don't use max() here, let it be negative if needed
                zero_place = len(fish_results) + 1  # Zeros get the next place after last fish place
            else:
                zero_points = 99  # If no one caught fish, zeros get 99 points
                zero_place = 1

            # Add zero-fish results
            for result in zero_results:
                result_tuple = (
                    zero_place,                         # 0: place
                    result.get("angler_name", ""),      # 1: name
                    result.get("num_fish", 0),          # 2: fish count
                    0.0,                                # 3: weight
                    float(result.get("big_bass_weight", 0)), # 4: big bass
                    zero_points,                        # 5: points
                    result.get("member", 1),            # 6: member status
                    result.get("id", 0)                 # 7: result id
                )
                individual_results.append(result_tuple)

            # Handle buy-ins per SABC bylaws Article IX:
            # Buy-ins get 4 points less than last place participant that weighed in fish
            if fish_results:
                # Find the points of the last place participant with fish (lowest points from fish only)
                last_fish_points = min([t[5] for t in individual_results if t[3] > 0])  # Only fish results
                buy_in_points = last_fish_points - 4  # 94 - 4 = 90
                buy_in_place = zero_place + 1  # One place after the zeros (9th place)
            else:
                buy_in_place = 1
                buy_in_points = 97  # 101 - 4

            # Don't add buy-ins to individual_results - they go in separate buy_in_results

            # Buy-in place already calculated above

            # Get buy-in results with calculated place and points
            buy_in_results_raw = qs.fetch_all(
                """SELECT a.name, a.member
                   FROM results r JOIN anglers a ON r.angler_id = a.id
                   WHERE r.tournament_id = :id AND r.buy_in = TRUE
                   AND NOT r.disqualified ORDER BY a.name""",
                {"id": tournament_id},
            )

            # Convert to format expected by template (tuple format)
            buy_in_results = []
            for result in buy_in_results_raw:
                buy_in_results.append((
                    result["name"],         # 0: name
                    buy_in_place,          # 1: place_finish
                    buy_in_points,         # 2: points
                    result["member"]       # 3: member
                ))

            # Get disqualified results
            disqualified_results_raw = qs.fetch_all(
                """SELECT a.name, a.member
                   FROM results r JOIN anglers a ON r.angler_id = a.id
                   WHERE r.tournament_id = :id AND r.disqualified = TRUE
                   ORDER BY a.name""",
                {"id": tournament_id},
            )

            # Convert disqualified results to tuple format
            disqualified_results = []
            for result in disqualified_results_raw:
                disqualified_results.append((
                    result["name"],         # 0: name
                    result["member"]        # 1: member status
                ))

            return {
                "user": user,
                "tournament": tournament_tuple,
                "tournament_stats": stats,
                "team_results": team_results,
                "individual_results": individual_results,
                "buy_in_place": buy_in_place,
                "buy_in_results": buy_in_results,
                "disqualified_results": disqualified_results,
            }
    except Exception:
        return None


async def get_awards_data(year: int = None, user=Depends(get_user_optional)):
    if year is None:
        year = datetime.now().year

    with engine.connect() as conn:
        qs = QueryService(conn)

        current_year = datetime.now().year
        available_years = qs.fetch_all(
            """SELECT DISTINCT year FROM events
               WHERE year IS NOT NULL AND year <= :year
               ORDER BY year DESC""",
            {"year": current_year},
        )
        years = [row["year"] for row in available_years]

        if not years:
            years = [datetime.now().year]

        if year not in years:
            year = years[0]

        # Get year statistics
        stats = qs.fetch_one(
            """SELECT COUNT(DISTINCT t.id) as total_tournaments,
               COUNT(DISTINCT a.id) as unique_anglers,
               SUM(r.num_fish) as total_fish,
               SUM(r.total_weight) as total_weight,
               AVG(r.total_weight) as avg_weight
               FROM tournaments t
               JOIN events e ON t.event_id = e.id
               JOIN results r ON t.id = r.tournament_id
               JOIN anglers a ON r.angler_id = a.id
               WHERE e.year = :year AND a.name != 'Admin User'""",
            {"year": year},
        ) or {
            "total_tournaments": 0,
            "unique_anglers": 0,
            "total_fish": 0,
            "total_weight": 0.0,
            "avg_weight": 0.0,
        }

        # Get AoY standings
        aoy_standings = qs.fetch_all(
            """SELECT a.name,
               SUM(r.points) as total_points,
               SUM(r.num_fish) as total_fish,
               SUM(r.total_weight) as total_weight,
               COUNT(r.tournament_id) as tournaments_fished
               FROM results r
               JOIN anglers a ON r.angler_id = a.id
               JOIN tournaments t ON r.tournament_id = t.id
               JOIN events e ON t.event_id = e.id
               WHERE e.year = :year AND a.member = TRUE AND a.name != 'Admin User'
               GROUP BY a.id, a.name
               ORDER BY total_points DESC""",
            {"year": year},
        )

        # Get heavy stringer
        heavy_stringer = qs.fetch_all(
            """SELECT a.name, r.total_weight, r.num_fish, e.name as tournament_name, e.date
               FROM results r
               JOIN anglers a ON r.angler_id = a.id
               JOIN tournaments t ON r.tournament_id = t.id
               JOIN events e ON t.event_id = e.id
               WHERE e.year = :year AND r.total_weight > 0 AND a.name != 'Admin User'
               ORDER BY r.total_weight DESC
               LIMIT 10""",
            {"year": year},
        )

        # Get big bass
        big_bass = qs.fetch_all(
            """SELECT a.name, r.big_bass_weight, e.name as tournament_name, e.date
               FROM results r
               JOIN anglers a ON r.angler_id = a.id
               JOIN tournaments t ON r.tournament_id = t.id
               JOIN events e ON t.event_id = e.id
               WHERE e.year = :year AND r.big_bass_weight >= 5.0 AND a.name != 'Admin User'
               ORDER BY r.big_bass_weight DESC
               LIMIT 10""",
            {"year": year},
        )

        return {
            "user": user,
            "current_year": year,
            "available_years": years,
            "aoy_standings": aoy_standings,
            "heavy_stringer": heavy_stringer,
            "big_bass": big_bass,
            "year_stats": stats,
        }
