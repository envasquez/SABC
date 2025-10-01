from fastapi import APIRouter, BackgroundTasks, Depends, Request

from core.deps import templates
from core.helpers.auth import require_auth
from routes.dependencies import db, get_lakes_list, get_ramps_for_lake
from routes.voting.helpers import get_poll_options, process_closed_polls

router = APIRouter()


@router.get("/polls")
async def polls(request: Request, background_tasks: BackgroundTasks, user=Depends(require_auth)):
    background_tasks.add_task(process_closed_polls)
    polls_data = db(
        "SELECT p.id, p.title, p.description, p.closes_at, p.closed, p.poll_type, p.starts_at, p.event_id, CASE WHEN CURRENT_TIMESTAMP < p.starts_at THEN 'upcoming' WHEN CURRENT_TIMESTAMP BETWEEN p.starts_at AND p.closes_at AND p.closed = FALSE THEN 'active' ELSE 'closed' END as status, EXISTS(SELECT 1 FROM poll_votes pv WHERE pv.poll_id = p.id AND pv.angler_id = :user_id) as user_has_voted FROM polls p ORDER BY p.closes_at DESC",
        {"user_id": user["id"]},
    )
    res = db("SELECT COUNT(*) FROM anglers WHERE member = TRUE")
    member_count = res[0][0] if res and len(res) > 0 else 0

    polls = []
    for poll_data in polls_data:
        unique_voters_result = db(
            "SELECT COUNT(DISTINCT angler_id) FROM poll_votes WHERE poll_id = :poll_id",
            {"poll_id": poll_data[0]},
        )
        unique_voters = (
            unique_voters_result[0][0]
            if unique_voters_result and len(unique_voters_result) > 0
            else 0
        )
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
                "options": get_poll_options(poll_data[0], user.get("is_admin")),
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
    return templates.TemplateResponse(
        "polls.html", {"request": request, "user": user, "polls": polls, "lakes_data": lakes_data}
    )
