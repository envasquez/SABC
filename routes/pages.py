import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from core.helpers.auth import get_user_optional, require_auth
from core.helpers.common_queries import get_members_with_last_tournament, get_officers
from core.helpers.template_helpers import render
from routes.dependencies import db, templates

router = APIRouter()


@router.get("/roster")
async def roster(request: Request, user=Depends(require_auth)):
    return render(
        "roster.html",
        request,
        user=user,
        members=get_members_with_last_tournament(),
        officers=get_officers(),
    )


@router.get("/calendar")
async def calendar_page(request: Request):
    user = get_user_optional(request)
    current_year = datetime.now().year
    next_year = current_year + 1

    def get_year_calendar_data(year):
        calendar_events = []
        tournament_events = db(
            "SELECT e.id as event_id, e.date, e.name, e.event_type, e.description, "
            "p.id as poll_id, p.title as poll_title, p.starts_at, p.closes_at, p.closed, "
            "t.id as tournament_id, t.complete as tournament_complete FROM events e "
            "LEFT JOIN polls p ON e.id = p.event_id LEFT JOIN tournaments t ON "
            "e.id = t.event_id WHERE strftime('%Y', e.date) = :year ORDER BY e.date",
            {"year": str(year)},
        )

        from core.helpers.calendar_utils import build_calendar_data_with_polls

        return build_calendar_data_with_polls(calendar_events, tournament_events, year)

    current_calendar_data, current_event_details, current_event_types = get_year_calendar_data(
        current_year
    )
    next_calendar_data, next_event_details, next_event_types = get_year_calendar_data(next_year)
    all_event_types = current_event_types | next_event_types
    return render(
        "calendar.html",
        request,
        user=user,
        current_year=current_year,
        next_year=next_year,
        current_calendar_data=current_calendar_data,
        current_event_details_json=json.dumps(current_event_details),
        next_calendar_data=next_calendar_data,
        next_event_details_json=json.dumps(next_event_details),
        event_types_present=all_event_types,
    )


@router.get("/home-paginated")
async def home_paginated(request: Request, page: int = 1):
    from core.config import settings

    user = get_user_optional(request)
    items_per_page = settings.ITEMS_PER_PAGE
    offset = (page - 1) * items_per_page
    tournaments = db(
        """
        SELECT t.id, e.date, e.name, e.description,
               l.display_name as lake_display_name, l.yaml_key as lake_name,
               ra.name as ramp_name, ra.google_maps_iframe as ramp_google_maps,
               l.google_maps_iframe as lake_google_maps,
               t.start_time, t.end_time, t.entry_fee, t.fish_limit, t.limit_type,
               t.is_team, t.is_paper, t.complete, t.poll_id,
               COUNT(DISTINCT r.angler_id) as total_anglers,
               SUM(r.num_fish) as total_fish,
               SUM(r.total_weight - r.dead_fish_penalty) as total_weight
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        LEFT JOIN lakes l ON t.lake_id = l.id
        LEFT JOIN ramps ra ON t.ramp_id = ra.id
        LEFT JOIN results r ON t.id = r.tournament_id AND NOT r.disqualified
        GROUP BY t.id, e.date, e.name, e.description,
                 l.display_name, l.yaml_key, ra.name, ra.google_maps_iframe, l.google_maps_iframe,
                 t.start_time, t.end_time, t.entry_fee, t.fish_limit, t.limit_type,
                 t.is_team, t.is_paper, t.complete, t.poll_id
        ORDER BY e.date DESC
        LIMIT :limit OFFSET :offset
    """,
        {"limit": items_per_page, "offset": offset},
    )
    total_tournaments = db("SELECT COUNT(*) FROM tournaments")[0][0]
    total_pages = (total_tournaments + items_per_page - 1) // items_per_page
    latest_news = db("""
        SELECT n.id, n.title, n.content, n.created_at, n.updated_at, n.priority,
               COALESCE(e.name, a.name) as display_author_name,
               a.name as original_author_name,
               e.name as editor_name
        FROM news n
        LEFT JOIN anglers a ON n.author_id = a.id
        LEFT JOIN anglers e ON n.last_edited_by = e.id
        WHERE n.published = 1 AND (n.expires_at IS NULL OR n.expires_at > datetime('now', 'localtime'))
        ORDER BY n.priority DESC, n.created_at DESC
        LIMIT 5
    """)
    tournaments_with_results = []
    for tournament in tournaments:
        tournament_id = tournament[0]
        top_results = db(
            """
            SELECT
                ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place,
                a1.name as angler1_name,
                a2.name as angler2_name,
                tr.total_weight,
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
            LIMIT 3
        """,
            {"tournament_id": tournament_id},
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
            "google_maps_iframe": tournament[7]
            or tournament[8],  # Use ramp maps if available, otherwise lake maps
            "start_time": tournament[9],
            "end_time": tournament[10],
            "entry_fee": tournament[11] or 25.0,
            "fish_limit": tournament[12] or 5,
            "limit_type": tournament[13] or "angler",
            "is_team": tournament[14],
            "is_paper": tournament[15],
            "complete": tournament[16],
            "poll_id": tournament[17],
            "total_anglers": tournament[18] or 0,
            "total_fish": tournament[19] or 0,
            "total_weight": tournament[20] or 0.0,
            "top_results": top_results,
            "event_date": tournament[1],  # Same as date, for template compatibility
        }
        tournaments_with_results.append(tournament_dict)

    window_size = 7
    if total_pages <= window_size:
        # Show all pages if total is less than window size
        page_range = list(range(1, total_pages + 1))
    else:
        half_window = window_size // 2
        if page <= half_window:
            page_range = list(range(1, window_size + 1))
        elif page >= total_pages - half_window:
            page_range = list(range(total_pages - window_size + 1, total_pages + 1))
        else:
            page_range = list(range(page - half_window, page + half_window + 1))

    start_index = offset + 1
    end_index = min(offset + items_per_page, total_tournaments)
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
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "start_index": start_index,
            "end_index": end_index,
            "total_tournaments": total_tournaments,
            "latest_news": latest_news,
        },
    )


@router.get("/health")
async def health_check():
    try:
        result = db("SELECT COUNT(*) as count FROM anglers")
        angler_count = result[0][0] if result else 0
        return {
            "status": "healthy",
            "database": "connected",
            "angler_count": angler_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@router.get("/{page:path}")
async def page(request: Request, page: str = "", p: int = 1):
    user = get_user_optional(request)
    if page in ["", "about", "bylaws", "awards"]:
        if not page:
            return await home_paginated(request, p)
        return render(f"{page}.html", request, user=user)
    raise HTTPException(status_code=404, detail="Page not found")
