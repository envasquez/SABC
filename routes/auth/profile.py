from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import case, desc, func, literal

from core.db_schema import Angler, Event, Result, TeamResult, Tournament, get_session
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
            session.query(
                func.coalesce(
                    func.max(Result.total_weight - func.coalesce(Result.dead_fish_penalty, 0)),
                    0,
                )
            )
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

        # Helper function to get team finishes for a specific year
        def get_year_finishes(year: int) -> Dict[str, int]:
            """Get 1st, 2nd, 3rd place team finishes for a specific year."""
            finishes_subquery = (
                session.query(
                    func.row_number().over(order_by=TeamResult.total_weight.desc()).label("place")
                )
                .select_from(TeamResult)
                .join(Tournament, TeamResult.tournament_id == Tournament.id)
                .join(Event, Tournament.event_id == Event.id)
                .filter(
                    (TeamResult.angler1_id == user["id"]) | (TeamResult.angler2_id == user["id"]),
                    Event.year == year,
                )
                .subquery()
            )

            finishes = session.query(
                func.sum(case((finishes_subquery.c.place == 1, 1), else_=0)).label("first"),
                func.sum(case((finishes_subquery.c.place == 2, 1), else_=0)).label("second"),
                func.sum(case((finishes_subquery.c.place == 3, 1), else_=0)).label("third"),
            ).first()

            # Count tournaments for this year
            year_tournaments = (
                session.query(func.count(func.distinct(Tournament.id)))
                .join(TeamResult, TeamResult.tournament_id == Tournament.id)
                .join(Event, Tournament.event_id == Event.id)
                .filter(
                    (TeamResult.angler1_id == user["id"]) | (TeamResult.angler2_id == user["id"]),
                    Event.year == year,
                )
                .scalar()
                or 0
            )

            return {
                "first": finishes[0] or 0 if finishes else 0,
                "second": finishes[1] or 0 if finishes else 0,
                "third": finishes[2] or 0 if finishes else 0,
                "tournaments": year_tournaments,
            }

        # Get team finishes for each year (2023-current)
        year_finishes = {}
        for year in range(2023, current_year + 1):
            year_finishes[year] = get_year_finishes(year)

        # All time finishes (team results from 2023+)
        all_time_finishes_subquery = (
            session.query(
                func.row_number().over(order_by=TeamResult.total_weight.desc()).label("place")
            )
            .select_from(TeamResult)
            .join(Tournament, TeamResult.tournament_id == Tournament.id)
            .join(Event, Tournament.event_id == Event.id)
            .filter(
                (TeamResult.angler1_id == user["id"]) | (TeamResult.angler2_id == user["id"]),
                Event.year >= 2023,
            )
            .subquery()
        )

        all_time_finishes = session.query(
            func.sum(case((all_time_finishes_subquery.c.place == 1, 1), else_=0)).label("first"),
            func.sum(case((all_time_finishes_subquery.c.place == 2, 1), else_=0)).label("second"),
            func.sum(case((all_time_finishes_subquery.c.place == 3, 1), else_=0)).label("third"),
        ).first()

        all_time_first = all_time_finishes[0] or 0 if all_time_finishes else 0
        all_time_second = all_time_finishes[1] or 0 if all_time_finishes else 0
        all_time_third = all_time_finishes[2] or 0 if all_time_finishes else 0

        # Monthly weight aggregation for chart (2023-current year)
        monthly_weights = (
            session.query(
                Event.year,
                func.extract("month", Event.date).label("month"),
                func.sum(Result.total_weight - func.coalesce(Result.dead_fish_penalty, 0)).label(
                    "total_weight"
                ),
            )
            .join(Tournament, Tournament.event_id == Event.id)
            .join(Result, Result.tournament_id == Tournament.id)
            .filter(
                Result.angler_id == user["id"],
                Result.disqualified.is_(False),
                Event.year >= 2023,
            )
            .group_by(Event.year, func.extract("month", Event.date))
            .order_by(Event.year, func.extract("month", Event.date))
            .all()
        )

        # Format monthly data for Chart.js
        monthly_data: Dict[str, Any] = {}
        for year in range(2023, current_year + 1):
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
                    (Result.total_weight - func.coalesce(Result.dead_fish_penalty, 0)).label(
                        "adjusted_weight"
                    ),
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
        except Exception as e:
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
        "profile.html",
        {
            "request": request,
            "user": user_profile,
            "stats": stats,
            "current_year": current_year,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
        },
    )
