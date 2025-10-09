from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import case, func
from sqlalchemy.orm import aliased

from core.db_schema import (
    Angler,
    Event,
    Lake,
    News,
    Poll,
    PollOption,
    PollVote,
    Ramp,
    Result,
    TeamResult,
    Tournament,
    engine,
    get_session,
)
from core.deps import templates
from core.helpers.auth import get_user_optional
from core.query_service import QueryService
from routes.dependencies import get_lakes_list, get_ramps_for_lake

router = APIRouter()


async def home_paginated(request: Request, page: int = 1):
    user = get_user_optional(request)
    items_per_page = 4
    offset = (page - 1) * items_per_page

    with get_session() as session:
        # Get total tournament count
        total_tournaments = (
            session.query(func.count(Tournament.id))
            .join(Event, Tournament.event_id == Event.id)
            .scalar()
            or 0
        )

        # Get tournaments with aggregated data
        tournaments_query = (
            session.query(
                Tournament.id,
                Event.date,
                Event.name,
                Event.description,
                Lake.display_name.label("lake_display_name"),
                Lake.yaml_key.label("lake_name"),
                Ramp.name.label("ramp_name"),
                Ramp.google_maps_iframe.label("ramp_google_maps"),
                Lake.google_maps_iframe.label("lake_google_maps"),
                Tournament.start_time,
                Tournament.end_time,
                Tournament.entry_fee,
                Tournament.fish_limit,
                Tournament.limit_type,
                Tournament.is_team,
                Tournament.is_paper,
                Tournament.complete,
                Tournament.poll_id,
                func.count(func.distinct(Result.angler_id)).label("total_anglers"),
                func.sum(Result.num_fish).label("total_fish"),
                func.sum(Result.total_weight - Result.dead_fish_penalty).label("total_weight"),
                Tournament.aoy_points,
            )
            .join(Event, Tournament.event_id == Event.id)
            .outerjoin(Lake, Tournament.lake_id == Lake.id)
            .outerjoin(Ramp, Tournament.ramp_id == Ramp.id)
            .outerjoin(
                Result,
                (Tournament.id == Result.tournament_id) & (Result.disqualified.is_(False)),
            )
            .outerjoin(
                Angler,
                (Result.angler_id == Angler.id) & (Angler.name != "Admin User"),
            )
            .group_by(
                Tournament.id,
                Event.date,
                Event.name,
                Event.description,
                Lake.display_name,
                Lake.yaml_key,
                Ramp.name,
                Ramp.google_maps_iframe,
                Lake.google_maps_iframe,
                Tournament.start_time,
                Tournament.end_time,
                Tournament.entry_fee,
                Tournament.fish_limit,
                Tournament.limit_type,
                Tournament.is_team,
                Tournament.is_paper,
                Tournament.complete,
                Tournament.poll_id,
                Tournament.aoy_points,
            )
            .order_by(Event.date.desc())
            .limit(items_per_page)
            .offset(offset)
            .all()
        )

        tournaments_with_results: List[Dict[str, Any]] = []
        for tournament in tournaments_query:
            tournament_id = tournament[0]
            poll_id = tournament[17]

            # Get top 3 team results for this tournament
            Angler1 = aliased(Angler)
            Angler2 = aliased(Angler)
            top_results_query = (
                session.query(
                    TeamResult.place_finish,
                    Angler1.name.label("angler1_name"),
                    Angler2.name.label("angler2_name"),
                    TeamResult.total_weight,
                    case((TeamResult.angler2_id.is_(None), 1), else_=2).label("team_size"),
                )
                .join(Angler1, TeamResult.angler1_id == Angler1.id)
                .outerjoin(Angler2, TeamResult.angler2_id == Angler2.id)
                .filter(
                    TeamResult.tournament_id == tournament_id,
                    Angler1.name != "Admin User",
                    (Angler2.name != "Admin User") | (Angler2.name.is_(None)),
                )
                .order_by(TeamResult.place_finish.asc())
                .limit(3)
                .all()
            )

            # Get poll data and check if user has voted
            import json

            poll_data = None
            user_has_voted = False
            poll_is_open = False

            if poll_id:
                # Get poll status
                poll = session.query(Poll).filter(Poll.id == poll_id).first()
                if poll:
                    from core.helpers.timezone import now_local

                    now = now_local()
                    poll_is_open = poll.starts_at <= now <= poll.closes_at

                # Get poll options with vote counts (for all users if they've voted)
                poll_options = (
                    session.query(
                        PollOption.id,
                        PollOption.option_text,
                        PollOption.option_data,
                        func.count(PollVote.id).label("vote_count"),
                    )
                    .outerjoin(PollVote, PollOption.id == PollVote.option_id)
                    .filter(PollOption.poll_id == poll_id)
                    .group_by(PollOption.id, PollOption.option_text, PollOption.option_data)
                    .all()
                )

                # Check if user has voted
                if user:
                    user_id = user.get("id") if isinstance(user, dict) else user.id
                    user_vote = (
                        session.query(PollVote)
                        .filter(PollVote.poll_id == poll_id, PollVote.angler_id == user_id)
                        .first()
                    )
                    user_has_voted = user_vote is not None

                # Only show poll data if user has voted
                if user_has_voted and poll_options:
                    poll_data = []
                    for opt in poll_options:
                        try:
                            option_data_dict = (
                                json.loads(opt.option_data) if opt.option_data else {}
                            )
                        except (json.JSONDecodeError, TypeError):
                            option_data_dict = {}

                        poll_data.append(
                            {
                                "option_text": opt.option_text,
                                "option_data": option_data_dict,
                                "vote_count": opt.vote_count,
                            }
                        )

            tournament_dict = {
                "id": tournament[0],
                "date": tournament[1],
                "name": tournament[2],
                "description": tournament[3],
                "lake_display_name": tournament[4],
                "lake_name": tournament[5],
                "ramp_name": tournament[6],
                "ramp_google_maps": tournament[7],
                "lake_google_maps": tournament[8],
                "google_maps_iframe": tournament[7] or tournament[8],
                "start_time": tournament[9],
                "end_time": tournament[10],
                "entry_fee": tournament[11] or 25.0,
                "fish_limit": tournament[12] or 5,
                "limit_type": tournament[13] or "per_person",
                "is_team": tournament[14],
                "is_paper": tournament[15],
                "complete": tournament[16],
                "poll_id": poll_id,
                "total_anglers": tournament[18] or 0,
                "total_fish": tournament[19] or 0,
                "total_weight": tournament[20] or 0.0,
                "aoy_points": tournament[21] if tournament[21] is not None else True,
                "top_results": top_results_query,
                "poll_data": poll_data,
                "user_has_voted": user_has_voted,
                "poll_is_open": poll_is_open,
            }
            print(
                f"BUTTON DEBUG: tournament_id={tournament[0]}, poll_id={poll_id}, user_has_voted={user_has_voted}, user={'yes' if user else 'no'}"
            )
            tournaments_with_results.append(tournament_dict)

        # Get member count
        member_count = (
            session.query(func.count(Angler.id)).filter(Angler.member.is_(True)).scalar() or 0
        )

        # Get latest news
        Author = aliased(Angler)
        Editor = aliased(Angler)
        latest_news = (
            session.query(
                News.id,
                News.title,
                News.content,
                News.created_at,
                News.updated_at,
                News.priority,
                func.coalesce(Editor.name, Author.name).label("display_author_name"),
                Author.name.label("original_author_name"),
                Editor.name.label("editor_name"),
            )
            .outerjoin(Author, News.author_id == Author.id)
            .outerjoin(Editor, News.last_edited_by == Editor.id)
            .filter(
                News.published.is_(True),
                (News.expires_at.is_(None)) | (News.expires_at > func.current_timestamp()),
            )
            .order_by(News.priority.desc(), News.created_at.desc())
            .limit(5)
            .all()
        )

    total_pages = (total_tournaments + items_per_page - 1) // items_per_page
    start_index = offset + 1
    end_index = min(offset + items_per_page, total_tournaments)

    # Calculate page range for pagination (show up to 5 page numbers)
    max_pages_shown = 5
    half_range = max_pages_shown // 2

    if total_pages <= max_pages_shown:
        page_range = range(1, total_pages + 1)
    else:
        start_page = max(1, page - half_range)
        end_page = min(total_pages, page + half_range)

        # Adjust if we're near the start or end
        if end_page - start_page + 1 < max_pages_shown:
            if start_page == 1:
                end_page = min(total_pages, start_page + max_pages_shown - 1)
            else:
                start_page = max(1, end_page - max_pages_shown + 1)

        page_range = range(start_page, end_page + 1)

    # Get year navigation links
    with engine.connect() as conn:
        qs = QueryService(conn)
        year_links = qs.get_tournament_years_with_first_id(items_per_page)

    # Get lakes data for poll results rendering
    lakes_data = [
        {
            "id": lake["id"],
            "name": lake["display_name"],
            "ramps": [
                {"id": r["id"], "name": r["name"].title()} for r in get_ramps_for_lake(lake["id"])
            ],
        }
        for lake in get_lakes_list()
    ]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "all_tournaments": tournaments_with_results,
            "current_page": page,
            "total_pages": total_pages,
            "page_range": page_range,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "start_index": start_index,
            "end_index": end_index,
            "total_tournaments": total_tournaments,
            "latest_news": latest_news,
            "member_count": member_count,
            "year_links": year_links,
            "lakes_data": lakes_data,
        },
    )


@router.get("/")
async def page(request: Request, p: int = 1):
    return await home_paginated(request, p)


@router.get("/{page:path}")
async def static_page(request: Request, page: str):
    user = get_user_optional(request)
    if page in ["about", "bylaws"]:
        return templates.TemplateResponse(f"{page}.html", {"request": request, "user": user})
    raise HTTPException(status_code=404, detail="Page not found")
