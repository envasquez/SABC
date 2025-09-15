import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_auth
from core.helpers.queries import get_poll_options_with_votes
from core.helpers.template_helpers import render
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


@router.get("/polls")
async def polls(request: Request, background_tasks: BackgroundTasks, user=Depends(require_auth)):
    from core.helpers.poll_processor import process_closed_polls

    background_tasks.add_task(process_closed_polls)

    polls_data = db(
        "SELECT p.id, p.title, p.description, p.closes_at, p.closed, p.poll_type, p.starts_at, p.event_id, CASE WHEN datetime('now', 'localtime') < datetime(p.starts_at) THEN 'upcoming' WHEN datetime('now', 'localtime') BETWEEN datetime(p.starts_at) AND datetime(p.closes_at) AND p.closed = 0 THEN 'active' ELSE 'closed' END as status, EXISTS(SELECT 1 FROM poll_votes pv WHERE pv.poll_id = p.id AND pv.angler_id = :user_id) as user_has_voted FROM polls p ORDER BY p.closes_at DESC",
        {"user_id": user["id"]},
    )

    member_count = db("SELECT COUNT(*) FROM anglers WHERE member = 1")[0][0]

    polls = []
    for poll_data in polls_data:
        unique_voters = db(
            "SELECT COUNT(DISTINCT angler_id) FROM poll_votes WHERE poll_id = :poll_id",
            {"poll_id": poll_data[0]},
        )[0][0]
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
                "options": get_poll_options_with_votes(poll_data[0], user.get("is_admin")),
                "member_count": member_count,
                "unique_voters": unique_voters,
                "participation_percent": round(
                    (unique_voters / member_count * 100) if member_count > 0 else 0, 1
                ),
            }
        )

    lakes_data = [
        {
            "id": lake_id,
            "name": lake_name,
            "ramps": [{"id": r[0], "name": r[1].title()} for r in get_ramps_for_lake(lake_id)],
        }
        for lake_id, lake_name, location in get_lakes_list()
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

        if not poll_check or poll_check[0][4] or poll_check[0][1]:
            return RedirectResponse(
                "/polls?error=Poll not found, already voted, or closed", status_code=302
            )

        if not (
            datetime.fromisoformat(poll_check[0][2])
            <= datetime.now()
            <= datetime.fromisoformat(poll_check[0][3])
        ):
            return RedirectResponse("/polls?error=Poll not accepting votes", status_code=302)

        poll_type = db("SELECT poll_type FROM polls WHERE id = :poll_id", {"poll_id": poll_id})[0][
            0
        ]

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
                actual_option_id = db("SELECT last_insert_rowid()")[0][0]
        else:
            actual_option_id = int(option_id)
            if not db(
                "SELECT id FROM poll_options WHERE id = :option_id AND poll_id = :poll_id",
                {"option_id": actual_option_id, "poll_id": poll_id},
            ):
                return RedirectResponse("/polls?error=Invalid option selected", status_code=302)

        db(
            "INSERT INTO poll_votes (poll_id, option_id, angler_id, voted_at) VALUES (:poll_id, :option_id, :angler_id, datetime('now'))",
            {"poll_id": poll_id, "option_id": actual_option_id, "angler_id": user["id"]},
        )
        return RedirectResponse("/polls?success=Vote cast successfully", status_code=302)

    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to cast vote: {str(e)}", status_code=302)
