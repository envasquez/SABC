"""Calendar, home, and awards routes."""

import calendar
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request

from routes.dependencies import db, find_lake_by_id, find_lake_data_by_db_name, templates, u

router = APIRouter()


def build_calendar_data_with_events(calendar_events, tournament_events, year=2025):
    """Build calendar data structure with holidays, tournaments, and poll information."""
    calendar.setfirstweekday(calendar.SUNDAY)
    all_events, event_details, event_types_present = {}, {}, set()

    for event in calendar_events:
        date_obj = datetime.strptime(event[0], "%Y-%m-%d")
        day = date_obj.day
        month = date_obj.month
        event_type = event[2]
        event_key = f"{date_obj.month}-{day}"
        if month not in all_events:
            all_events[month] = {}
        if day not in all_events[month]:
            all_events[month][day] = []
        all_events[month][day].append({"type": event_type, "title": event[1]})
        event_types_present.add(event_type)
        if event_key not in event_details:
            event_details[event_key] = []
        event_details[event_key].append(
            {
                "title": event[1],
                "type": event_type,
                "description": event[3] if event[3] else "",
                "date": event[0],
            }
        )

    for event in tournament_events:
        date_obj = datetime.strptime(event[1], "%Y-%m-%d")
        day = date_obj.day
        month = date_obj.month
        event_key = f"{month}-{day}"
        event_type = event[3]
        if month not in all_events:
            all_events[month] = {}
        if day not in all_events[month]:
            all_events[month][day] = []
        all_events[month][day].append({"type": event_type, "title": event[2]})
        event_types_present.add(event_type)

        now, event_date = datetime.now().date(), date_obj.date()
        poll_id, poll_closed, tournament_id, tournament_complete = (
            event[5],
            event[9],
            event[10],
            event[11],
        )
        poll_status = poll_link = tournament_link = None

        if poll_id:
            if event_date > now:
                poll_status, poll_link = (
                    ("active" if not poll_closed else "closed"),
                    f"/polls#{poll_id}",
                )
            else:
                poll_status, poll_link = "results", f"/polls#{poll_id}"
        if tournament_id and tournament_complete:
            tournament_link = f"/tournaments/{tournament_id}"

        if event_key not in event_details:
            event_details[event_key] = []
        event_details[event_key].append(
            {
                "title": event[2],
                "type": event_type,
                "description": event[4] if event[4] else "",
                "date": event[1],
                "event_id": event[0],
                "poll_id": poll_id,
                "poll_status": poll_status,
                "poll_link": poll_link,
                "tournament_id": tournament_id,
                "tournament_complete": tournament_complete,
                "tournament_link": tournament_link,
            }
        )

    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    calendar_structure = []

    for month_idx, month_name in enumerate(months, 1):
        cal = calendar.monthcalendar(year, month_idx)
        weeks = []
        for week in cal:
            week_days = []
            for day in week:
                if day == 0:
                    week_days.append("")
                else:
                    day_str = str(day)
                    if month_idx in all_events and day in all_events[month_idx]:
                        events_for_day = all_events[month_idx][day]
                        has_sabc = any(e["type"] == "sabc_tournament" for e in events_for_day)
                        has_holiday = any(e["type"] == "holiday" for e in events_for_day)
                        has_other = any(e["type"] == "other_tournament" for e in events_for_day)
                        if has_sabc:
                            day_str += "†"
                        elif has_other:
                            day_str += "‡"
                        elif has_holiday:
                            day_str += "*"
                    week_days.append(day_str)
            weeks.append(week_days)
        calendar_structure.append([month_name, weeks])

    return calendar_structure, event_details, event_types_present


@router.get("/calendar")
async def calendar_page(request: Request):
    """Calendar page with dynamic event loading from database."""
    user, current_year, next_year = u(request), datetime.now().year, datetime.now().year + 1

    def get_year_calendar_data(year):
        all_events = db(
            """
            SELECT e.id as event_id, e.date, e.name, e.event_type, e.description,
                   p.id as poll_id, p.title as poll_title, p.starts_at, p.closes_at, p.closed,
                   t.id as tournament_id, t.complete as tournament_complete
            FROM events e LEFT JOIN polls p ON e.id = p.event_id LEFT JOIN tournaments t ON e.id = t.event_id
            WHERE strftime('%Y', e.date) = :year ORDER BY e.date""",
            {"year": str(year)},
        )

        # Separate calendar events (holidays) from tournament events
        calendar_events = []
        tournament_events = []

        for event in all_events:
            if event[3] == "holiday":  # event_type
                # Format for calendar_events: (date, name, event_type, description)
                calendar_events.append((event[1], event[2], event[3], event[4]))
            else:
                # Keep full tournament event data
                tournament_events.append(event)

        return build_calendar_data_with_events(calendar_events, tournament_events, year)

    current_calendar_data, current_event_details, current_event_types = get_year_calendar_data(
        current_year
    )
    next_calendar_data, next_event_details, next_event_types = get_year_calendar_data(next_year)

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": user,
            "current_year": current_year,
            "next_year": next_year,
            "current_calendar_data": current_calendar_data,
            "current_event_details_json": json.dumps(current_event_details),
            "next_calendar_data": next_calendar_data,
            "next_event_details_json": json.dumps(next_event_details),
            "event_types_present": current_event_types | next_event_types,
        },
    )


@router.get("/home-paginated")
async def home_paginated(request: Request, page: int = 1):
    user, items_per_page, offset = u(request), 4, (page - 1) * 4

    all_tournaments_query = db(
        """
        SELECT t.id, t.name, t.lake_name, t.ramp_name, t.start_time, t.end_time, t.fish_limit, t.entry_fee, t.is_team, t.is_paper, t.complete, t.poll_id,
               t.limit_type, e.date as event_date, e.description, (SELECT COUNT(*) FROM results r WHERE r.tournament_id = t.id) as participants,
               (SELECT MAX(r.total_weight - r.dead_fish_penalty) FROM results r WHERE r.tournament_id = t.id AND NOT r.disqualified) as winning_weight
        FROM tournaments t JOIN events e ON t.event_id = e.id WHERE e.event_type = 'sabc_tournament' ORDER BY e.date DESC LIMIT :limit OFFSET :offset
    """,
        {"limit": items_per_page, "offset": offset},
    )

    total_tournaments = db(
        "SELECT COUNT(*) FROM tournaments t JOIN events e ON t.event_id = e.id WHERE e.event_type = 'sabc_tournament'"
    )[0][0]
    total_pages = (total_tournaments + items_per_page - 1) // items_per_page

    tournaments = []
    for t in all_tournaments_query:
        tournament = {
            "id": t[0],
            "name": t[1],
            "lake_name": t[2],
            "ramp_name": t[3],
            "start_time": t[4],
            "end_time": t[5],
            "fish_limit": t[6] or 5,
            "entry_fee": t[7] or 25.0,
            "is_team": t[8],
            "is_paper": t[9],
            "complete": t[10],
            "poll_id": t[11],
            "limit_type": t[12] or "angler",
            "event_date": t[13],
            "description": t[14],
            "tournament_stats": {"participants": t[15] or 0, "winning_weight": float(t[16] or 0.0)}
            if t[15]
            else None,
            "google_maps_iframe": None,
            "poll_data": None,
        }

        if tournament["complete"] and tournament["tournament_stats"]:
            top_3_teams = db(
                "SELECT tr.total_weight, tr.place_finish, a1.name as angler1_name, a2.name as angler2_name FROM team_results tr LEFT JOIN anglers a1 ON tr.angler1_id = a1.id LEFT JOIN anglers a2 ON tr.angler2_id = a2.id WHERE tr.tournament_id = :tournament_id AND tr.place_finish <= 3 ORDER BY tr.place_finish ASC",
                {"tournament_id": tournament["id"]},
            )
            tournament["tournament_stats"]["top_3"] = []
            for result in top_3_teams:

                def format_name(name):
                    return (
                        f"{name.split()[0][0]}.{name.split()[-1]}"
                        if name and len(name.split()) >= 2
                        else name
                    )

                formatted_angler1, formatted_angler2 = (
                    format_name(result[2]),
                    format_name(result[3]),
                )
                team_name = (
                    f"{formatted_angler1} / {formatted_angler2}"
                    if formatted_angler2
                    else (formatted_angler1 or "Unknown Team")
                )
                tournament["tournament_stats"]["top_3"].append(
                    {
                        "name": team_name,
                        "weight": float(result[0] or 0.0),
                        "place": result[1],
                        "angler1": result[2],
                        "angler2": result[3],
                    }
                )

        if tournament["lake_name"]:
            yaml_key, lake_info, display_name = find_lake_data_by_db_name(tournament["lake_name"])
            if display_name:
                tournament["lake_name"] = display_name
            if lake_info:
                if tournament["ramp_name"] and "ramps" in lake_info:
                    for ramp in lake_info["ramps"]:
                        if ramp["name"].lower() == tournament["ramp_name"].lower():
                            tournament["google_maps_iframe"] = ramp.get("google_maps", "")
                            break
                if not tournament["google_maps_iframe"]:
                    tournament["google_maps_iframe"] = lake_info.get("google_maps", "")

        if tournament["poll_id"] and not tournament["complete"]:
            poll_options = db(
                "SELECT po.option_text, po.option_data, COUNT(pv.id) as vote_count FROM poll_options po LEFT JOIN poll_votes pv ON po.id = pv.option_id WHERE po.poll_id = :poll_id GROUP BY po.id, po.option_text, po.option_data ORDER BY vote_count DESC",
                {"poll_id": tournament["poll_id"]},
            )
            tournament["poll_data"] = []
            for option in poll_options:
                try:
                    option_data = json.loads(option[1]) if option[1] else {}
                except:
                    option_data = {}
                tournament["poll_data"].append(
                    {
                        "option_text": option[0],
                        "option_data": option_data,
                        "vote_count": option[2],
                        "lake_id": option_data.get("lake_id"),
                        "lake_name": find_lake_by_id(option_data.get("lake_id"), "name")
                        if option_data.get("lake_id")
                        else None,
                    }
                )
        tournaments.append(tournament)

    upcoming = db(
        "SELECT t.id, t.name, t.lake_name, e.date FROM tournaments t JOIN events e ON t.event_id = e.id WHERE e.date >= date('now') AND e.event_type = 'sabc_tournament' ORDER BY e.date ASC LIMIT 1"
    )
    next_tournament = None
    if upcoming:
        lake_name = upcoming[0][2]
        if lake_name:
            yaml_key, lake_info, display_name = find_lake_data_by_db_name(lake_name)
            if display_name:
                lake_name = display_name
        next_tournament = {
            "id": upcoming[0][0],
            "name": upcoming[0][1],
            "lake_name": lake_name,
            "event_date": upcoming[0][3],
        }

    member_count = db("SELECT COUNT(*) FROM anglers WHERE member = 1")[0][0]
    latest_news = db(
        "SELECT n.id, n.title, n.content, n.created_at, n.priority, COALESCE(e.name, a.name) as author_name FROM news n LEFT JOIN anglers a ON n.author_id = a.id LEFT JOIN anglers e ON n.last_edited_by = e.id WHERE n.published = 1 ORDER BY n.priority DESC, n.created_at DESC LIMIT 5"
    )

    start_index, end_index = offset + 1, min(offset + items_per_page, total_tournaments)
    page_range = list(range(max(1, page - 2), min(total_pages + 1, page + 3)))

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "all_tournaments": tournaments,
            "next_tournament": next_tournament,
            "latest_news": latest_news,
            "member_count": member_count,
            "current_page": page,
            "total_pages": total_pages,
            "total_tournaments": total_tournaments,
            "start_index": start_index,
            "end_index": end_index,
            "page_range": page_range,
        },
    )


@router.get("/awards")
@router.get("/awards/{year}")
async def awards(request: Request, year: Optional[int] = None):
    user = u(request)
    if year is None:
        year = datetime.now().year
    current_year = datetime.now().year
    available_years = db(
        "SELECT DISTINCT year FROM events WHERE year IS NOT NULL AND year <= :year ORDER BY year DESC",
        {"year": current_year},
    )
    years = [row[0] for row in available_years] or [datetime.now().year]
    if year not in years:
        year = years[0]

    # Calculate AOY standings
    aoy_standings = db(
        """
        WITH tournament_standings AS (
            SELECT r.angler_id, r.tournament_id, r.total_weight - COALESCE(r.dead_fish_penalty, 0) as adjusted_weight, r.num_fish, r.disqualified, r.buy_in,
                   DENSE_RANK() OVER (PARTITION BY r.tournament_id ORDER BY CASE WHEN r.disqualified = 1 THEN 0 ELSE r.total_weight - COALESCE(r.dead_fish_penalty, 0) END DESC) as place_finish,
                   COUNT(*) OVER (PARTITION BY r.tournament_id) as total_participants
            FROM results r JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id WHERE e.year = :year
        ),
        points_calc AS (SELECT angler_id, tournament_id, adjusted_weight, num_fish, place_finish, CASE WHEN disqualified = 1 THEN 0 ELSE 101 - place_finish END as points FROM tournament_standings)
        SELECT a.name, SUM(CASE WHEN a.member = 1 THEN pc.points ELSE 0 END) as total_points, SUM(pc.num_fish) as total_fish, SUM(pc.adjusted_weight) as total_weight, COUNT(DISTINCT pc.tournament_id) as events_fished
        FROM anglers a JOIN points_calc pc ON a.id = pc.angler_id WHERE a.member = 1 GROUP BY a.id, a.name ORDER BY total_points DESC, total_weight DESC
    """,
        {"year": year},
    )

    # Heavy stringer & Big bass
    heavy_stringer = db(
        "SELECT a.name, r.total_weight, r.num_fish, (substr(e.date, 1, 4) || ' ' || CASE substr(e.date, 6, 2) WHEN '01' THEN 'January' WHEN '02' THEN 'February' WHEN '03' THEN 'March' WHEN '04' THEN 'April' WHEN '05' THEN 'May' WHEN '06' THEN 'June' WHEN '07' THEN 'July' WHEN '08' THEN 'August' WHEN '09' THEN 'September' WHEN '10' THEN 'October' WHEN '11' THEN 'November' WHEN '12' THEN 'December' END || ' Tournament') as tournament_name, e.date FROM results r JOIN anglers a ON r.angler_id = a.id JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id WHERE e.year = :year AND r.total_weight > 0 ORDER BY r.total_weight DESC LIMIT 1",
        {"year": year},
    )
    big_bass = db(
        "SELECT a.name, r.big_bass_weight, (substr(e.date, 1, 4) || ' ' || CASE substr(e.date, 6, 2) WHEN '01' THEN 'January' WHEN '02' THEN 'February' WHEN '03' THEN 'March' WHEN '04' THEN 'April' WHEN '05' THEN 'May' WHEN '06' THEN 'June' WHEN '07' THEN 'July' WHEN '08' THEN 'August' WHEN '09' THEN 'September' WHEN '10' THEN 'October' WHEN '11' THEN 'November' WHEN '12' THEN 'December' END || ' Tournament') as tournament_name, e.date FROM results r JOIN anglers a ON r.angler_id = a.id JOIN tournaments t ON r.tournament_id = t.id JOIN events e ON t.event_id = e.id WHERE e.year = :year AND r.big_bass_weight >= 5.0 ORDER BY r.big_bass_weight DESC LIMIT 1",
        {"year": year},
    )
    year_stats = db(
        "SELECT COUNT(DISTINCT t.id) as total_tournaments, COUNT(DISTINCT a.id) as unique_anglers, SUM(r.num_fish) as total_fish, SUM(r.total_weight) as total_weight, AVG(r.total_weight) as avg_weight FROM tournaments t JOIN events e ON t.event_id = e.id JOIN results r ON t.id = r.tournament_id JOIN anglers a ON r.angler_id = a.id WHERE e.year = :year",
        {"year": year},
    )
    stats = year_stats[0] if year_stats else (0, 0, 0, 0.0, 0.0)

    return templates.TemplateResponse(
        "awards.html",
        {
            "request": request,
            "user": user,
            "current_year": year,
            "available_years": years,
            "aoy_standings": aoy_standings,
            "heavy_stringer": heavy_stringer[0] if heavy_stringer else None,
            "big_bass": big_bass[0] if big_bass else None,
            "year_stats": {
                "total_tournaments": stats[0],
                "unique_anglers": stats[1],
                "total_fish": stats[2],
                "total_weight": stats[3],
                "avg_weight": stats[4],
            },
        },
    )
