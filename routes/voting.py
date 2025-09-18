import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import RedirectResponse

from core.db_schema import engine
from core.deps import render
from core.helpers.auth import require_auth
from core.query_service import QueryService
from routes.dependencies import (
    db,
    find_lake_by_id,
    find_ramp_name_by_id,
    get_lakes_list,
    get_ramps_for_lake,
    time_format_filter,
    validate_lake_ramp_combo,
)

router = APIRouter()


def _get_poll_options(poll_id: int, is_admin: bool = False):
    """Helper to get poll options with votes."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_poll_options_with_votes(poll_id, include_details=is_admin)


@router.get("/polls")
async def polls(request: Request, background_tasks: BackgroundTasks, user=Depends(require_auth)):
    from core.helpers.poll_processor import process_closed_polls

    background_tasks.add_task(process_closed_polls)

    polls_data = db(
        "SELECT p.id, p.title, p.description, p.closes_at, p.closed, p.poll_type, p.starts_at, p.event_id, CASE WHEN CURRENT_TIMESTAMP < p.starts_at THEN 'upcoming' WHEN CURRENT_TIMESTAMP BETWEEN p.starts_at AND p.closes_at AND p.closed = FALSE THEN 'active' ELSE 'closed' END as status, EXISTS(SELECT 1 FROM poll_votes pv WHERE pv.poll_id = p.id AND pv.angler_id = :user_id) as user_has_voted FROM polls p ORDER BY p.closes_at DESC",
        {"user_id": user["id"]},
    )

    res = db("SELECT COUNT(*) FROM anglers WHERE member = TRUE")
    member_count = res[0][0] if res and len(res) > 0 else 0

    polls = []
    for poll_data in polls_data:
        unique_voters = db(
            "SELECT COUNT(DISTINCT angler_id) FROM poll_votes WHERE poll_id = :poll_id",
            {"poll_id": poll_data[0]},
        )
        unique_voters = res[0][0] if res and len(res) > 0 else 0
        polls.append(
            {
                "id": poll_data[0],
                "title": poll_data[1],
                "description": poll_data[2] if poll_data[2] else "",
                "closes_at": poll_data[3],
                "starts_at": poll_data[6],
                "closed": bool(poll_data[4]),
                "poll_type": poll_data[5],
                "event_id": poll_data[7],
                "status": poll_data[8],
                "user_has_voted": bool(poll_data[9]),
                "options": _get_poll_options(poll_data[0], user.get("is_admin")),
                "member_count": member_count,
                "unique_voters": unique_voters,
                "participation_percent": round(
                    (unique_voters / member_count * 100) if member_count > 0 else 0, 1
                ),
            }
        )

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

    return render("polls.html", request, user=user, polls=polls, lakes_data=lakes_data)


@router.post("/polls/{poll_id}/vote")
async def vote_in_poll(
    request: Request, poll_id: int, option_id: str = Form(), user=Depends(require_auth)
):
    if not user.get("member"):
        return RedirectResponse("/polls?error=Only members can vote", status_code=302)

    try:
        poll_check = db(
            "SELECT p.id, p.closed, p.starts_at, p.closes_at, EXISTS(SELECT 1 FROM poll_votes pv WHERE pv.poll_id = p.id AND pv.angler_id = :user_id) as already_voted FROM polls p WHERE p.id = :poll_id",
            {"poll_id": poll_id, "user_id": user["id"]},
        )

        if not poll_check or len(poll_check) == 0:
            return RedirectResponse("/polls?error=Poll not found", status_code=302)

        poll_row = poll_check[0]
        already_voted = poll_row[4]
        is_closed = poll_row[1]
        starts_at = poll_row[2]
        closes_at = poll_row[3]

        if already_voted or is_closed:
            return RedirectResponse(
                "/polls?error=Poll not found, already voted, or closed", status_code=302
            )

        if not (
            datetime.fromisoformat(starts_at) <= datetime.now() <= datetime.fromisoformat(closes_at)
        ):
            return RedirectResponse("/polls?error=Poll not accepting votes", status_code=302)

        res = db("SELECT poll_type FROM polls WHERE id = :poll_id", {"poll_id": poll_id})
        poll_type = res[0][0] if res and len(res) > 0 else None

        if not poll_type:
            return RedirectResponse("/polls?error=Invalid poll", status_code=302)

        if poll_type == "tournament_location":
            vote_data = json.loads(option_id)
            lake_id_int = int(vote_data["lake_id"])

            if not all(
                f in vote_data for f in ["lake_id", "ramp_id", "start_time", "end_time"]
            ) or not validate_lake_ramp_combo(lake_id_int, vote_data["ramp_id"]):
                return RedirectResponse("/polls?error=Invalid vote data", status_code=302)

            lake_name, ramp_name = (
                find_lake_by_id(lake_id_int, "name"),
                find_ramp_name_by_id(vote_data["ramp_id"]),
            )
            if not lake_name or not ramp_name:
                return RedirectResponse("/polls?error=Lake or ramp not found", status_code=302)

            option_text = f"{lake_name} - {ramp_name} ({time_format_filter(vote_data['start_time'])} to {time_format_filter(vote_data['end_time'])})"
            existing_option = db(
                "SELECT id FROM poll_options WHERE poll_id = :poll_id AND option_text = :option_text",
                {"poll_id": poll_id, "option_text": option_text},
            )

            if existing_option:
                actual_option_id = existing_option[0][0]
            else:
                vote_data["lake_id"] = lake_id_int
                db(
                    "INSERT INTO poll_options (poll_id, option_text, option_data) VALUES (:poll_id, :option_text, :option_data)",
                    {
                        "poll_id": poll_id,
                        "option_text": option_text,
                        "option_data": json.dumps(vote_data),
                    },
                )
                res = db("SELECT lastval()")
                actual_option_id = res[0][0] if res and len(res) > 0 else None
        else:
            actual_option_id = int(option_id)
            if not db(
                "SELECT id FROM poll_options WHERE id = :option_id AND poll_id = :poll_id",
                {"option_id": actual_option_id, "poll_id": poll_id},
            ):
                return RedirectResponse("/polls?error=Invalid option selected", status_code=302)

        db(
            "INSERT INTO poll_votes (poll_id, option_id, angler_id, voted_at) VALUES (:poll_id, :option_id, :angler_id, NOW())",
            {"poll_id": poll_id, "option_id": actual_option_id, "angler_id": user["id"]},
        )
        return RedirectResponse("/polls?success=Vote cast successfully", status_code=302)

    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to cast vote: {str(e)}", status_code=302)
