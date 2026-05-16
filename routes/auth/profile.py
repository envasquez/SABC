from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import case, desc, func, literal
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Angler, Event, Result, TeamResult, Tournament, get_session
from core.enums import TOURNAMENT_DATA_START_YEAR
from core.helpers.logging import get_logger
from routes.dependencies import get_current_user, templates

router = APIRouter()
logger = get_logger("auth.profile")


@router.get("/profile")
async def profile_page(request: Request) -> Response:
    if not (user := get_current_user(request)):
        return RedirectResponse("/login")

    with get_session() as session:
        # Get user profile data
        angler = session.query(Angler).filter(Angler.id == user["id"]).first()
        if not angler:
            return RedirectResponse("/login")

        user_profile: Dict[str, Any] = {
            "id": angler.id,
            "name": angler.name,
            "email": angler.email,
            "member": bool(angler.member),
            "is_admin": bool(angler.is_admin),
            "phone": angler.phone,
            "year_joined": angler.year_joined,
            "created_at": angler.created_at,
        }

        from core.helpers.timezone import now_local

        current_year = now_local().year

        # Tournaments count
        tournaments_count = (
            session.query(func.count(func.distinct(Tournament.id)))
            .join(Result, Result.tournament_id == Tournament.id)
            .join(Event, Tournament.event_id == Event.id)
            .filter(Result.angler_id == user["id"], Result.disqualified.is_(False))
            .scalar()
            or 0
        )

        # Best weight
        best_weight = (
            session.query(func.coalesce(func.max(Result.total_weight), 0))
            .join(Tournament, Result.tournament_id == Tournament.id)
            .filter(Result.angler_id == user["id"], Result.disqualified.is_(False))
            .scalar()
            or 0
        )

        # Big bass
        big_bass = (
            session.query(func.coalesce(func.max(Result.big_bass_weight), 0))
            .join(Tournament, Result.tournament_id == Tournament.id)
            .filter(Result.angler_id == user["id"], Result.disqualified.is_(False))
            .scalar()
            or 0
        )

        # Team tournaments count
        team_tournaments_count = (
            session.query(func.count(func.distinct(Tournament.id)))
            .join(TeamResult, TeamResult.tournament_id == Tournament.id)
            .join(Event, Tournament.event_id == Event.id)
            .filter((TeamResult.angler1_id == user["id"]) | (TeamResult.angler2_id == user["id"]))
            .scalar()
            or 0
        )

        # Best team weight
        best_team_weight = (
            session.query(func.coalesce(func.max(TeamResult.total_weight), 0))
            .join(Tournament, TeamResult.tournament_id == Tournament.id)
            .filter((TeamResult.angler1_id == user["id"]) | (TeamResult.angler2_id == user["id"]))
            .scalar()
            or 0
        )

        # Team finishes per year — single windowed query across all years
        # instead of 2 queries × N years. Adapted from the
        # roster.py:get_member_stats pattern, but scoped to the current user.
        year_finishes: Dict[int, Dict[str, int]] = {}
        for year in range(TOURNAMENT_DATA_START_YEAR, current_year + 1):
            year_finishes[year] = {"first": 0, "second": 0, "third": 0, "tournaments": 0}

        ranked_per_year_subq = (
            session.query(
                TeamResult.tournament_id.label("tournament_id"),
                TeamResult.angler1_id.label("angler1_id"),
                TeamResult.angler2_id.label("angler2_id"),
                Event.year.label("event_year"),
                func.dense_rank()
                .over(
                    partition_by=TeamResult.tournament_id,
                    order_by=TeamResult.total_weight.desc(),
                )
                .label("place"),
            )
            .select_from(TeamResult)
            .join(Tournament, TeamResult.tournament_id == Tournament.id)
            .join(Event, Tournament.event_id == Event.id)
            .filter(Event.year >= TOURNAMENT_DATA_START_YEAR)
            .subquery()
        )

        # Filter to the user's rows, aggregate finishes per year. One query.
        per_year_rows = (
            session.query(
                ranked_per_year_subq.c.event_year.label("event_year"),
                func.sum(case((ranked_per_year_subq.c.place == 1, 1), else_=0)).label("first"),
                func.sum(case((ranked_per_year_subq.c.place == 2, 1), else_=0)).label("second"),
                func.sum(case((ranked_per_year_subq.c.place == 3, 1), else_=0)).label("third"),
                func.count(func.distinct(ranked_per_year_subq.c.tournament_id)).label(
                    "tournaments"
                ),
            )
            .filter(
                (ranked_per_year_subq.c.angler1_id == user["id"])
                | (ranked_per_year_subq.c.angler2_id == user["id"])
            )
            .group_by(ranked_per_year_subq.c.event_year)
            .all()
        )
        for row in per_year_rows:
            yr = int(row.event_year)
            if yr in year_finishes:
                year_finishes[yr] = {
                    "first": int(row.first or 0),
                    "second": int(row.second or 0),
                    "third": int(row.third or 0),
                    "tournaments": int(row.tournaments or 0),
                }

        # All time finishes (team results since data start)
        # First, rank ALL participants within each tournament
        all_time_ranked_subquery = (
            session.query(
                TeamResult.tournament_id,
                TeamResult.angler1_id,
                TeamResult.angler2_id,
                func.dense_rank()
                .over(
                    partition_by=TeamResult.tournament_id,
                    order_by=TeamResult.total_weight.desc(),
                )
                .label("place"),
            )
            .select_from(TeamResult)
            .join(Tournament, TeamResult.tournament_id == Tournament.id)
            .join(Event, Tournament.event_id == Event.id)
            .filter(Event.year >= TOURNAMENT_DATA_START_YEAR)
            .subquery()
        )

        # Then filter to user's results and count finishes
        all_time_finishes = (
            session.query(
                func.sum(case((all_time_ranked_subquery.c.place == 1, 1), else_=0)).label("first"),
                func.sum(case((all_time_ranked_subquery.c.place == 2, 1), else_=0)).label("second"),
                func.sum(case((all_time_ranked_subquery.c.place == 3, 1), else_=0)).label("third"),
            )
            .filter(
                (all_time_ranked_subquery.c.angler1_id == user["id"])
                | (all_time_ranked_subquery.c.angler2_id == user["id"])
            )
            .first()
        )

        all_time_first = all_time_finishes[0] or 0 if all_time_finishes else 0
        all_time_second = all_time_finishes[1] or 0 if all_time_finishes else 0
        all_time_third = all_time_finishes[2] or 0 if all_time_finishes else 0

        # Monthly weight aggregation for chart (since data start through current year)
        # Uses individual results as primary source
        # Falls back to team_results for tournaments without individual data
        from sqlalchemy import text

        from core.query_service.dialect_helpers import DialectName, month_extract, year_extract

        # Detect database dialect for compatibility
        bind = session.bind
        dialect_name: DialectName = (
            "sqlite" if bind is not None and bind.dialect.name == "sqlite" else "postgresql"
        )
        year_col = year_extract("e.date", dialect_name)
        month_col = month_extract("e.date", dialect_name)

        # Query individual weights, falling back to team_results when needed
        # For team-only tournaments, attribute team weight to angler1
        monthly_weights_query = text(f"""
            WITH all_weights AS (
                -- Individual results (primary source)
                SELECT {year_col} as year,
                       {month_col} as month,
                       r.total_weight as weight
                FROM results r
                JOIN tournaments t ON r.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE r.angler_id = :user_id
                  AND r.disqualified = FALSE
                  AND {year_col} >= {TOURNAMENT_DATA_START_YEAR}
                UNION ALL
                -- Team results (only for tournaments without individual data)
                -- Attribute team weight to angler1 to avoid double-counting
                SELECT {year_col} as year,
                       {month_col} as month,
                       tr.total_weight as weight
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE tr.angler1_id = :user_id
                  AND {year_col} >= {TOURNAMENT_DATA_START_YEAR}
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
                UNION ALL
                -- Angler2 gets 0 weight for team-only tournaments (just for participation tracking)
                SELECT {year_col} as year,
                       {month_col} as month,
                       0 as weight
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE tr.angler2_id = :user_id
                  AND {year_col} >= {TOURNAMENT_DATA_START_YEAR}
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
            )
            SELECT year, month, SUM(weight) as total_weight
            FROM all_weights
            GROUP BY year, month
            ORDER BY year, month
        """)

        monthly_weights = session.execute(monthly_weights_query, {"user_id": user["id"]}).fetchall()

        # Format monthly data for Chart.js
        monthly_data: Dict[str, Any] = {}
        for year in range(TOURNAMENT_DATA_START_YEAR, current_year + 1):
            monthly_data[str(year)] = [0] * 12

        for year, month, weight in monthly_weights:
            year_str = str(year)
            month_idx = int(month) - 1  # Convert to 0-indexed
            if year_str in monthly_data and 0 <= month_idx < 12:
                monthly_data[year_str][month_idx] = float(weight or 0)

        # AOY position (complex query - keeping similar structure)
        aoy_position: Optional[int] = None
        try:
            # This is a complex query with CTEs - using text query would be acceptable
            # but let's try to do it with ORM

            # First subquery: tournament_standings
            tournament_standings_subquery = (
                session.query(
                    Result.angler_id,
                    Result.tournament_id,
                    Result.total_weight.label("adjusted_weight"),
                    Result.num_fish,
                    Result.disqualified,
                    Result.buy_in,
                    func.dense_rank()
                    .over(
                        partition_by=Result.tournament_id,
                        order_by=desc(
                            case(
                                (
                                    Result.disqualified.is_(True),
                                    literal(0),
                                ),
                                else_=Result.total_weight
                                - func.coalesce(Result.dead_fish_penalty, 0),
                            )
                        ),
                    )
                    .label("place_finish"),
                    func.count()
                    .over(partition_by=Result.tournament_id)
                    .label("total_participants"),
                )
                .join(Tournament, Result.tournament_id == Tournament.id)
                .join(Event, Tournament.event_id == Event.id)
                .filter(Event.year == current_year)
                .subquery()
            )

            # Second subquery: points_calc
            points_calc_subquery = (
                session.query(
                    tournament_standings_subquery.c.angler_id,
                    tournament_standings_subquery.c.tournament_id,
                    tournament_standings_subquery.c.adjusted_weight,
                    tournament_standings_subquery.c.num_fish,
                    tournament_standings_subquery.c.place_finish,
                    case(
                        (tournament_standings_subquery.c.disqualified.is_(True), 0),
                        else_=101 - tournament_standings_subquery.c.place_finish,
                    ).label("points"),
                )
                .select_from(tournament_standings_subquery)
                .subquery()
            )

            # Third subquery: aoy_standings
            aoy_standings_subquery = (
                session.query(
                    Angler.id,
                    Angler.name,
                    func.sum(
                        case((Angler.member.is_(True), points_calc_subquery.c.points), else_=0)
                    ).label("total_points"),
                    func.sum(points_calc_subquery.c.adjusted_weight).label("total_weight"),
                    func.row_number()
                    .over(
                        order_by=[
                            desc(
                                func.sum(
                                    case(
                                        (Angler.member.is_(True), points_calc_subquery.c.points),
                                        else_=0,
                                    )
                                )
                            ),
                            desc(func.sum(points_calc_subquery.c.adjusted_weight)),
                        ]
                    )
                    .label("position"),
                )
                .join(points_calc_subquery, Angler.id == points_calc_subquery.c.angler_id)
                .filter(Angler.member.is_(True))
                .group_by(Angler.id, Angler.name)
                .subquery()
            )

            # Final query: get position for current user
            aoy_result = (
                session.query(aoy_standings_subquery.c.position)
                .filter(aoy_standings_subquery.c.id == user["id"])
                .first()
            )
            if aoy_result:
                aoy_position = aoy_result[0]
        except SQLAlchemyError as e:
            logger.warning(f"Failed to calculate AOY standings for user {user['id']}: {e}")
            # aoy_position remains None, which is acceptable

        stats = {
            "tournaments": tournaments_count,
            "best_weight": best_weight,
            "big_bass": big_bass,
            "team_tournaments": team_tournaments_count,
            "best_team_weight": best_team_weight,
            "year_finishes": year_finishes,
            "all_time_first": all_time_first,
            "all_time_second": all_time_second,
            "all_time_third": all_time_third,
            "aoy_position": aoy_position,
            "monthly_data": monthly_data,
        }

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "user": user_profile,
            "stats": stats,
            "current_year": current_year,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
        },
    )
