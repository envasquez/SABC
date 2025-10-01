from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.helpers.logging import get_logger
from routes.auth.profile_queries import (
    all_time_finishes_query,
    aoy_position_query,
    best_weight_query,
    big_bass_query,
    current_finishes_query,
    tournaments_count_query,
)
from routes.dependencies import db, templates, u

router = APIRouter()
logger = get_logger("auth.profile")


@router.get("/profile")
async def profile_page(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")
    user_data = db(
        "SELECT id, name, email, member, is_admin, phone, year_joined, created_at FROM anglers WHERE id = :id",
        {"id": user["id"]},
    )
    if not user_data:
        return RedirectResponse("/login")
    user_profile = {
        "id": user_data[0][0],
        "name": user_data[0][1],
        "email": user_data[0][2],
        "member": bool(user_data[0][3]),
        "is_admin": bool(user_data[0][4]),
        "phone": user_data[0][5],
        "year_joined": user_data[0][6],
        "created_at": user_data[0][7],
    }
    current_year = datetime.now().year
    res = db(tournaments_count_query(), {"user_id": user["id"]})
    tournaments_count = res[0][0] if res and len(res) > 0 else 0
    res = db(best_weight_query(), {"user_id": user["id"]})
    best_weight = res[0][0] if res and len(res) > 0 else 0
    res = db(big_bass_query(), {"user_id": user["id"]})
    big_bass = res[0][0] if res and len(res) > 0 else 0
    current_finishes = db(
        current_finishes_query(), {"user_id": user["id"], "current_year": current_year}
    )
    current_first, current_second, current_third = (
        current_finishes[0] if current_finishes else (0, 0, 0)
    )
    all_time_finishes = db(all_time_finishes_query(), {"user_id": user["id"]})
    all_time_first, all_time_second, all_time_third = (
        all_time_finishes[0] if all_time_finishes else (0, 0, 0)
    )
    aoy_position = None
    try:
        aoy_standings = db(
            aoy_position_query(), {"current_year": current_year, "user_id": user["id"]}
        )
        if aoy_standings:
            aoy_position = aoy_standings[0][0]
    except Exception:
        pass
    stats = {
        "tournaments": tournaments_count,
        "best_weight": best_weight,
        "big_bass": big_bass,
        "current_first": current_first or 0,
        "current_second": current_second or 0,
        "current_third": current_third or 0,
        "all_time_first": all_time_first or 0,
        "all_time_second": all_time_second or 0,
        "all_time_third": all_time_third or 0,
        "aoy_position": aoy_position,
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
