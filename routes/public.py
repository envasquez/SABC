from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.filters import time_format_filter
from core.lakes import (
    find_lake_by_id,
    find_ramp_name_by_id,
    get_lakes_list,
    get_ramps_for_lake,
    validate_lake_ramp_combo,
)

from .dependencies import datetime, db, json, templates, u

router = APIRouter()


@router.get("/roster")
async def roster(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")
    members = db(
        """SELECT DISTINCT a.name, a.email, a.member, a.is_admin, a.active, a.created_at, a.phone, CASE WHEN a.member = 0 THEN (SELECT e.date FROM results r JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id WHERE r.angler_id = a.id ORDER BY e.date DESC LIMIT 1) ELSE NULL END as last_tournament_date FROM anglers a WHERE a.active = 1 OR EXISTS (SELECT 1 FROM results r WHERE r.angler_id = a.id) OR EXISTS (SELECT 1 FROM team_results tr WHERE tr.angler1_id = a.id OR tr.angler2_id = a.id) ORDER BY a.member DESC, a.name"""
    )
    officers = db(
        """SELECT op.position, a.name, a.email, a.phone FROM officer_positions op JOIN anglers a ON op.angler_id = a.id WHERE op.year = 2025 ORDER BY CASE op.position WHEN 'President' THEN 1 WHEN 'Vice President' THEN 2 WHEN 'Secretary' THEN 3 WHEN 'Treasurer' THEN 4 WHEN 'Weigh-master' THEN 5 WHEN 'Assistant Weigh-master' THEN 6 WHEN 'Technology Director' THEN 7 ELSE 8 END"""
    )
    return templates.TemplateResponse(
        "roster.html", {"request": request, "user": user, "members": members, "officers": officers}
    )


@router.get("/polls")
async def polls(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")
    polls_data = db(
        """SELECT p.id, p.title, p.description, p.closes_at, p.closed, p.poll_type, p.starts_at, p.event_id, CASE WHEN datetime('now', 'localtime') < datetime(p.starts_at) THEN 'upcoming' WHEN datetime('now', 'localtime') BETWEEN datetime(p.starts_at) AND datetime(p.closes_at) AND p.closed = 0 THEN 'active' ELSE 'closed' END as status, EXISTS(SELECT 1 FROM poll_votes pv WHERE pv.poll_id = p.id AND pv.angler_id = :user_id) as user_has_voted FROM polls p ORDER BY p.closes_at DESC""",
        {"user_id": user["id"]},
    )
    polls = []
    for poll_data in polls_data:
        poll_id = poll_data[0]
        options_data = db(
            """SELECT po.id, po.option_text, po.option_data, COUNT(pv.id) as vote_count FROM poll_options po LEFT JOIN poll_votes pv ON po.id = pv.option_id WHERE po.poll_id = :poll_id GROUP BY po.id, po.option_text, po.option_data ORDER BY po.id""",
            {"poll_id": poll_id},
        )
        options = []
        for option_data in options_data:
            option_dict = {
                "id": option_data[0],
                "text": option_data[1],
                "data": option_data[2],
                "vote_count": option_data[3],
            }
            if user.get("is_admin"):
                option_dict["votes"] = [
                    {"vote_id": v[0], "voter_name": v[1], "voted_at": v[2]}
                    for v in db(
                        """SELECT pv.id, a.name as voter_name, pv.voted_at FROM poll_votes pv JOIN anglers a ON pv.angler_id = a.id WHERE pv.option_id = :option_id ORDER BY pv.voted_at DESC""",
                        {"option_id": option_data[0]},
                    )
                ]
            options.append(option_dict)
        member_count = db("SELECT COUNT(*) FROM anglers WHERE member = 1 AND active = 1")[0][0]
        unique_voters = db(
            "SELECT COUNT(DISTINCT angler_id) FROM poll_votes WHERE poll_id = :poll_id",
            {"poll_id": poll_id},
        )[0][0]
        polls.append(
            {
                "id": poll_id,
                "title": poll_data[1],
                "description": poll_data[2] if poll_data[2] else "",
                "closes_at": poll_data[3],
                "starts_at": poll_data[6],
                "closed": bool(poll_data[4]),
                "poll_type": poll_data[5],
                "event_id": poll_data[7],
                "status": poll_data[8],
                "user_has_voted": bool(poll_data[9]),
                "options": options,
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
    return templates.TemplateResponse(
        "polls.html", {"request": request, "user": user, "polls": polls, "lakes_data": lakes_data}
    )


@router.post("/polls/{poll_id}/vote")
async def vote_in_poll(request: Request, poll_id: int, option_id: str = Form()):
    if not (user := u(request)):
        return RedirectResponse("/login")
    if not user.get("member"):
        return RedirectResponse("/polls?error=Only members can vote", status_code=302)
    try:
        poll_check = db(
            """SELECT p.id, p.closed, p.starts_at, p.closes_at, EXISTS(SELECT 1 FROM poll_votes pv WHERE pv.poll_id = p.id AND pv.angler_id = :user_id) as already_voted FROM polls p WHERE p.id = :poll_id""",
            {"poll_id": poll_id, "user_id": user["id"]},
        )
        if not poll_check:
            return RedirectResponse("/polls?error=Poll not found", status_code=302)
        poll = poll_check[0]
        if poll[4] or poll[1]:
            return RedirectResponse("/polls?error=Already voted or poll closed", status_code=302)
        now, starts_at, closes_at = (
            datetime.now(),
            datetime.fromisoformat(poll[2]),
            datetime.fromisoformat(poll[3]),
        )
        if now < starts_at or now > closes_at:
            return RedirectResponse("/polls?error=Poll not accepting votes", status_code=302)
        poll_type = db("SELECT poll_type FROM polls WHERE id = :poll_id", {"poll_id": poll_id})[0][
            0
        ]
        if poll_type == "tournament_location":
            vote_data = json.loads(option_id)
            if not all(
                field in vote_data for field in ["lake_id", "ramp_id", "start_time", "end_time"]
            ):
                return RedirectResponse("/polls?error=Invalid vote data", status_code=302)
            lake_id_int = int(vote_data["lake_id"])
            if not validate_lake_ramp_combo(lake_id_int, vote_data["ramp_id"]):
                return RedirectResponse("/polls?error=Invalid lake/ramp combo", status_code=302)
            lake_name, ramp_name = (
                find_lake_by_id(lake_id_int, "name"),
                find_ramp_name_by_id(vote_data["ramp_id"]),
            )
            if not lake_name or not ramp_name:
                return RedirectResponse("/polls?error=Lake or ramp not found", status_code=302)
            option_text = f"{lake_name} - {ramp_name} ({time_format_filter(vote_data['start_time'])} to {time_format_filter(vote_data['end_time'])})"
            existing_option = db(
                """SELECT id FROM poll_options WHERE poll_id = :poll_id AND option_text = :option_text""",
                {"poll_id": poll_id, "option_text": option_text},
            )
            if existing_option:
                actual_option_id = existing_option[0][0]
            else:
                vote_data["lake_id"] = lake_id_int
                db(
                    """INSERT INTO poll_options (poll_id, option_text, option_data) VALUES (:poll_id, :option_text, :option_data)""",
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
                """SELECT id FROM poll_options WHERE id = :option_id AND poll_id = :poll_id""",
                {"option_id": actual_option_id, "poll_id": poll_id},
            ):
                return RedirectResponse("/polls?error=Invalid option", status_code=302)
        db(
            """INSERT INTO poll_votes (poll_id, option_id, angler_id, voted_at) VALUES (:poll_id, :option_id, :angler_id, datetime('now'))""",
            {"poll_id": poll_id, "option_id": actual_option_id, "angler_id": user["id"]},
        )
        return RedirectResponse("/polls?success=Vote cast successfully!", status_code=302)
    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to cast vote: {str(e)}", status_code=302)


@router.get("/profile")
async def profile(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")
    user_id, current_year = user["id"], datetime.now().year
    tournaments = db(
        "SELECT COUNT(*) FROM results r JOIN tournaments t ON r.tournament_id = t.id WHERE r.angler_id = :id AND t.complete = 1",
        {"id": user_id},
    )[0][0]
    best_weight = float(
        db(
            "SELECT MAX(total_weight - dead_fish_penalty) FROM results r JOIN tournaments t ON r.tournament_id = t.id WHERE r.angler_id = :id AND t.complete = 1 AND NOT r.disqualified",
            {"id": user_id},
        )[0][0]
        or 0
    )
    big_bass = float(
        db(
            "SELECT MAX(big_bass_weight) FROM results r JOIN tournaments t ON r.tournament_id = t.id WHERE r.angler_id = :id AND t.complete = 1",
            {"id": user_id},
        )[0][0]
        or 0
    )

    def get_finishes(year_filter=None):
        yc, params = (
            ("AND e.year = :year", {"id": user_id, "year": year_filter})
            if year_filter
            else ("", {"id": user_id})
        )
        tf = db(
            f"SELECT tr.place_finish FROM team_results tr JOIN tournaments t ON tr.tournament_id = t.id JOIN events e ON t.event_id = e.id WHERE (tr.angler1_id = :id OR tr.angler2_id = :id) AND t.complete = 1 {yc}",
            params,
        )
        return (
            tf
            if tf
            else db(
                f"SELECT r.place_finish FROM results r JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id WHERE r.angler_id = :id AND t.complete = 1 AND r.place_finish > 0 {yc}",
                params,
            )
        )

    cyf, atf = get_finishes(current_year), get_finishes()
    cf1, cf2, cf3 = (
        len([f for f in cyf if f[0] == 1]),
        len([f for f in cyf if f[0] == 2]),
        len([f for f in cyf if f[0] == 3]),
    )
    af1, af2, af3 = (
        len([f for f in atf if f[0] == 1]),
        len([f for f in atf if f[0] == 2]),
        len([f for f in atf if f[0] == 3]),
    )
    aoy_points = (
        db(
            "SELECT SUM(r.points) FROM results r JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id WHERE r.angler_id = :id AND e.year = :year AND t.complete = 1",
            {"id": user_id, "year": current_year},
        )[0][0]
        or 0
    )
    aoy_position = (
        db(
            "SELECT COUNT(*) + 1 FROM (SELECT r.angler_id, SUM(r.points) as tp FROM results r JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id JOIN anglers a ON r.angler_id = a.id WHERE e.year = :year AND t.complete = 1 AND a.member = 1 GROUP BY r.angler_id HAVING tp > :user_points)",
            {"year": current_year, "user_points": aoy_points},
        )[0][0]
        if aoy_points > 0
        else None
    )
    cyt = db(
        "SELECT COUNT(*) FROM results r JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id WHERE r.angler_id = :id AND e.year = :year AND t.complete = 1",
        {"id": user_id, "year": current_year},
    )[0][0]
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "stats": {
                "tournaments": tournaments,
                "best_weight": best_weight,
                "big_bass": big_bass,
                "first_place": cf1,
                "second_place": cf2,
                "third_place": cf3,
                "aoy_points": aoy_points,
                "aoy_position": aoy_position,
                "current_year_tournaments": cyt,
                "points_behind": 0,
                "avg_points": 0,
                "all_time_first": af1,
                "all_time_second": af2,
                "all_time_third": af3,
                "current_first": cf1,
                "current_second": cf2,
                "current_third": cf3,
            },
            "current_year": current_year,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/profile/update")
async def update_profile(
    request: Request, email: str = Form(), phone: str = Form(), year_joined: int = Form()
):
    if not (user := u(request)):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Session expired"}, status_code=401
        )
    try:
        db(
            "UPDATE anglers SET email=:email, phone=:phone, year_joined=:year_joined WHERE id=:id",
            {
                "email": email.lower().strip(),
                "phone": phone.strip() if phone else None,
                "year_joined": year_joined,
                "id": user["id"],
            },
        )
        return RedirectResponse("/profile?success=Updated!", status_code=302)
    except:
        return RedirectResponse("/profile?error=Failed", status_code=302)


@router.post("/profile/delete")
async def delete_profile(request: Request, confirm: str = Form()):
    if not (user := u(request)):
        return RedirectResponse("/login")
    if confirm.strip() != "DELETE":
        return RedirectResponse("/profile?error=Must type DELETE", status_code=302)
    try:
        db("UPDATE anglers SET active=0 WHERE id=:id", {"id": user["id"]})
        request.session.clear()
        return templates.TemplateResponse(
            "login.html", {"request": request, "success": "Account deleted"}
        )
    except:
        return RedirectResponse("/profile?error=Failed", status_code=302)
