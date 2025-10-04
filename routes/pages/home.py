from fastapi import APIRouter, HTTPException, Request

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import get_user_optional
from core.query_service import QueryService
from routes.dependencies import db
from routes.pages.home_queries import get_top_results_query, get_tournaments_query

router = APIRouter()


async def home_paginated(request: Request, page: int = 1):
    user = get_user_optional(request)
    items_per_page = 4
    offset = (page - 1) * items_per_page
    tournaments = db(get_tournaments_query(), {"limit": items_per_page, "offset": offset})
    res = db("SELECT COUNT(*) FROM tournaments t JOIN events e ON t.event_id = e.id")
    total_tournaments = res[0][0] if res and len(res) > 0 else 0
    total_pages = (total_tournaments + items_per_page - 1) // items_per_page
    tournaments_with_results = []
    for tournament in tournaments:
        tournament_id = tournament[0]
        top_results = db(get_top_results_query(), {"tournament_id": tournament_id})
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
            "poll_id": tournament[17],
            "total_anglers": tournament[18] or 0,
            "total_fish": tournament[19] or 0,
            "total_weight": tournament[20] or 0.0,
            "aoy_points": tournament[21] if len(tournament) > 21 else True,
            "top_results": top_results,
        }
        tournaments_with_results.append(tournament_dict)
    res = db("SELECT COUNT(*) FROM anglers WHERE member = TRUE")
    member_count = res[0][0] if res and len(res) > 0 else 0
    latest_news = db("""
        SELECT n.id, n.title, n.content, n.created_at, n.updated_at, n.priority,
               COALESCE(e.name, a.name) as display_author_name,
               a.name as original_author_name,
               e.name as editor_name
        FROM news n
        LEFT JOIN anglers a ON n.author_id = a.id
        LEFT JOIN anglers e ON n.last_edited_by = e.id
        WHERE n.published = TRUE AND (n.expires_at IS NULL OR n.expires_at > CURRENT_TIMESTAMP)
        ORDER BY n.priority DESC, n.created_at DESC
        LIMIT 5
    """)
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
