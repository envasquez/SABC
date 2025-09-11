"""Public-facing router module for SABC."""

import calendar
import json
from datetime import datetime
from typing import Optional

from fastapi import Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.db_helpers import (
    get_poll_options_with_votes,
    get_tournament_stats,
)
from routes.dependencies import (
    db,
    find_lake_by_id,
    find_ramp_name_by_id,
    get_lakes_list,
    get_ramps_for_lake,
    load_lakes_data,
    templates,
    time_format_filter,
    u,
    validate_lake_ramp_combo,
)

from fastapi import APIRouter

router = APIRouter()


@router.get("/roster")
async def roster(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")

    # Get all active members and tournament participants with last tournament date for guests
    members = db("""
        SELECT DISTINCT a.name, a.email, a.member, a.is_admin, a.active, a.created_at, a.phone,
               CASE
                   WHEN a.member = 0 THEN (
                       SELECT e.date
                       FROM results r
                       JOIN tournaments t ON r.tournament_id = t.id
                       JOIN events e ON t.event_id = e.id
                       WHERE r.angler_id = a.id
                       ORDER BY e.date DESC
                       LIMIT 1
                   )
                   ELSE NULL
               END as last_tournament_date
        FROM anglers a
        WHERE a.active = 1
           OR EXISTS (
               SELECT 1 FROM results r WHERE r.angler_id = a.id
           )
           OR EXISTS (
               SELECT 1 FROM team_results tr WHERE tr.angler1_id = a.id OR tr.angler2_id = a.id
           )
        ORDER BY a.member DESC, a.name
    """)

    # Get officer positions
    officers = db("""
        SELECT o.position, a.name, a.email, a.phone
        FROM officers o
        JOIN anglers a ON o.angler_id = a.id
        WHERE o.year = 2025
        ORDER BY
            CASE o.position
                WHEN 'President' THEN 1
                WHEN 'Vice President' THEN 2
                WHEN 'Secretary' THEN 3
                WHEN 'Treasurer' THEN 4
                WHEN 'Weigh-master' THEN 5
                WHEN 'Assistant Weigh-master' THEN 6
                WHEN 'Technology Director' THEN 7
                ELSE 8
            END
    """)

    return templates.TemplateResponse(
        "roster.html",
        {
            "request": request,
            "user": user,
            "members": members,
            "officers": officers,
        },
    )


@router.get("/polls")
async def polls(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")

    # Get polls with computed status fields and user's vote status
    polls_data = db(
        """
        SELECT p.id, p.title, p.description, p.closes_at, p.closed, p.poll_type,
               p.starts_at, p.event_id,
               CASE
                   WHEN datetime('now', 'localtime') < datetime(p.starts_at) THEN 'upcoming'
                   WHEN datetime('now', 'localtime') BETWEEN datetime(p.starts_at) AND datetime(p.closes_at) AND p.closed = 0 THEN 'active'
                   ELSE 'closed'
               END as status,
               EXISTS(
                   SELECT 1 FROM poll_votes pv
                   WHERE pv.poll_id = p.id AND pv.angler_id = :user_id
               ) as user_has_voted
        FROM polls p
        ORDER BY p.closes_at DESC
    """,
        {"user_id": user["id"]},
    )

    # Convert to list of dicts for easier template access
    member_count = db("SELECT COUNT(*) FROM anglers WHERE member = 1 AND active = 1")[0][0]

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

    # Get lakes and ramps data for tournament location voting from YAML
    lakes_data = [
        {
            "id": lake_id,
            "name": lake_name,
            "ramps": [{"id": r[0], "name": r[1].title()} for r in get_ramps_for_lake(lake_id)],
        }
        for lake_id, lake_name, location in get_lakes_list()
    ]

    return templates.TemplateResponse(
        "polls.html",
        {
            "request": request,
            "user": user,
            "polls": polls,
            "lakes_data": lakes_data,
        },
    )


@router.post("/polls/{poll_id}/vote")
async def vote_in_poll(request: Request, poll_id: int, option_id: str = Form()):
    """Cast a vote in a poll (members only)."""
    if not (user := u(request)):
        return RedirectResponse("/login")

    if not user.get("member"):
        return RedirectResponse("/polls?error=Only members can vote", status_code=302)

    try:
        # Check if poll is active and user hasn't voted yet
        poll_check = db(
            """
            SELECT p.id, p.closed, p.starts_at, p.closes_at,
                   EXISTS(SELECT 1 FROM poll_votes pv WHERE pv.poll_id = p.id AND pv.angler_id = :user_id) as already_voted
            FROM polls p
            WHERE p.id = :poll_id
        """,
            {"poll_id": poll_id, "user_id": user["id"]},
        )

        if not poll_check:
            return RedirectResponse("/polls?error=Poll not found", status_code=302)

        if poll_check[0][4]:  # already_voted
            return RedirectResponse(
                "/polls?error=You have already voted in this poll", status_code=302
            )
        if poll_check[0][1]:  # closed
            return RedirectResponse("/polls?error=This poll is closed", status_code=302)
        if not (
            datetime.fromisoformat(poll_check[0][2])
            <= datetime.now()
            <= datetime.fromisoformat(poll_check[0][3])
        ):
            return RedirectResponse(
                "/polls?error=This poll is not currently accepting votes", status_code=302
            )

        poll_type = db("SELECT poll_type FROM polls WHERE id = :poll_id", {"poll_id": poll_id})[0][
            0
        ]

        if poll_type == "tournament_location":
            # Handle dynamic tournament location vote
            try:
                vote_data = json.loads(option_id)

                # Validate the vote data structure
                required_fields = ["lake_id", "ramp_id", "start_time", "end_time"]
                if not all(field in vote_data for field in required_fields):
                    return RedirectResponse("/polls?error=Invalid vote data", status_code=302)

                # Convert lake_id to integer for validation (HTML forms send strings)
                try:
                    lake_id_int = int(vote_data["lake_id"])
                except (ValueError, TypeError):
                    return RedirectResponse("/polls?error=Invalid lake ID", status_code=302)

                # Validate lake and ramp exist and are associated using YAML data
                if not validate_lake_ramp_combo(lake_id_int, vote_data["ramp_id"]):
                    return RedirectResponse(
                        "/polls?error=Invalid lake and ramp combination", status_code=302
                    )

                # Create or find existing poll option for this combination
                if not (lake_name := find_lake_by_id(lake_id_int, "name")) or not (
                    ramp_name := find_ramp_name_by_id(vote_data["ramp_id"])
                ):
                    return RedirectResponse("/polls?error=Lake or ramp not found", status_code=302)

                option_text = f"{lake_name} - {ramp_name} ({time_format_filter(vote_data['start_time'])} to {time_format_filter(vote_data['end_time'])})"

                # Check if this exact option already exists
                existing_option = db(
                    """
                    SELECT id FROM poll_options
                    WHERE poll_id = :poll_id AND option_text = :option_text
                """,
                    {"poll_id": poll_id, "option_text": option_text},
                )

                if existing_option:
                    actual_option_id = existing_option[0][0]
                else:
                    # Create new option with corrected lake_id as integer
                    corrected_vote_data = vote_data.copy()
                    corrected_vote_data["lake_id"] = lake_id_int
                    db(
                        """
                        INSERT INTO poll_options (poll_id, option_text, option_data)
                        VALUES (:poll_id, :option_text, :option_data)
                    """,
                        {
                            "poll_id": poll_id,
                            "option_text": option_text,
                            "option_data": json.dumps(corrected_vote_data),
                        },
                    )
                    actual_option_id = db("SELECT last_insert_rowid()")[0][0]

            except json.JSONDecodeError:
                return RedirectResponse("/polls?error=Invalid vote format", status_code=302)
            except Exception as e:
                return RedirectResponse(
                    f"/polls?error=Error processing vote: {str(e)}", status_code=302
                )

        else:
            # Handle traditional pre-defined option voting
            try:
                actual_option_id = int(option_id)
            except ValueError:
                return RedirectResponse("/polls?error=Invalid option selected", status_code=302)

            # Verify option exists for this poll
            option_check = db(
                """
                SELECT id FROM poll_options WHERE id = :option_id AND poll_id = :poll_id
            """,
                {"option_id": actual_option_id, "poll_id": poll_id},
            )

            if not option_check:
                return RedirectResponse("/polls?error=Invalid option selected", status_code=302)

        # Cast the vote
        db(
            """
            INSERT INTO poll_votes (poll_id, option_id, angler_id, voted_at)
            VALUES (:poll_id, :option_id, :angler_id, datetime('now'))
        """,
            {"poll_id": poll_id, "option_id": actual_option_id, "angler_id": user["id"]},
        )

        return RedirectResponse(
            "/polls?success=Vote cast successfully - Thank you for voting!", status_code=302
        )

    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to cast vote: {str(e)}", status_code=302)


@router.get("/tournaments/{tournament_id}")
async def tournament_results(request: Request, tournament_id: int):
    """Display tournament results page matching reference site format."""
    user = u(request)

    # Get tournament details with event info
    tournament = db(
        """
        SELECT t.id, t.event_id, e.date, e.name, e.description,
               t.lake_name, t.ramp_name,
               t.entry_fee, t.fish_limit, t.complete,
               e.event_type
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        WHERE t.id = :tournament_id
    """,
        {"tournament_id": tournament_id},
    )

    if not tournament:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    tournament = tournament[0]

    # Get tournament statistics
    tournament_stats = get_tournament_stats(tournament_id, tournament[8])

    # Get team results if this is a team tournament
    team_results = db(
        """
        SELECT
            ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place,
            a1.name || ' / ' || a2.name as team_name,
            (SELECT SUM(num_fish) FROM results r WHERE r.angler_id IN (tr.angler1_id, tr.angler2_id) AND r.tournament_id = tr.tournament_id) as num_fish,
            tr.total_weight,
            a1.member as member1,
            a2.member as member2
        FROM team_results tr
        JOIN anglers a1 ON tr.angler1_id = a1.id
        JOIN anglers a2 ON tr.angler2_id = a2.id
        WHERE tr.tournament_id = :tournament_id
        ORDER BY tr.total_weight DESC
    """,
        {"tournament_id": tournament_id},
    )

    # Get individual results with correct SABC scoring
    # First, get the count of MEMBERS with fish for calculating last place with fish points
    # Guests don't count for points calculation
    members_with_fish = db(
        """
        SELECT COUNT(*)
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        AND r.num_fish > 0
        AND NOT r.disqualified
        AND a.member = 1  -- Only count members for points calculation
    """,
        {"tournament_id": tournament_id},
    )[0][0]

    # Calculate points correctly per SABC bylaws:
    # - MEMBERS with fish: 100 for 1st, 99 for 2nd, etc.
    # - GUESTS: Always 0 points regardless of performance
    # - Zero fish members (no buy-in): 2 points less than last place member with fish
    # - Buy-ins (members): 4 points less than last place member with fish
    last_place_with_fish_points = 100 - members_with_fish + 1

    individual_results = db(
        """
        SELECT
            ROW_NUMBER() OVER (ORDER BY CASE WHEN r.num_fish > 0 THEN 0 ELSE 1 END, (r.total_weight - r.dead_fish_penalty) DESC, r.big_bass_weight DESC, r.buy_in, a.name) as place,
            a.name, r.num_fish, r.total_weight - r.dead_fish_penalty as final_weight, r.big_bass_weight,
            CASE WHEN a.member = 0 THEN 0 WHEN r.num_fish > 0 AND a.member = 1 THEN 100 - ROW_NUMBER() OVER (PARTITION BY CASE WHEN r.num_fish > 0 AND a.member = 1 THEN 1 ELSE 0 END ORDER BY (r.total_weight - r.dead_fish_penalty) DESC, r.big_bass_weight DESC) + 1 WHEN r.buy_in = 1 AND a.member = 1 THEN :last_place_points - 4 WHEN a.member = 1 THEN :last_place_points - 2 ELSE 0 END as points, a.member
        FROM results r JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id AND NOT r.disqualified AND r.buy_in = 0
        ORDER BY CASE WHEN r.num_fish > 0 THEN 0 ELSE 1 END, (r.total_weight - r.dead_fish_penalty) DESC, r.big_bass_weight DESC, a.name
    """,
        {"tournament_id": tournament_id, "last_place_points": last_place_with_fish_points},
    )

    # Get buy-in results separately for dedicated buy-ins table
    # All buy-ins get the same place finish (one position after last individual finisher)
    # But get points according to SABC rule: last place with fish points minus 4
    buy_in_place = db(
        """
        SELECT COUNT(*) + 1
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        AND NOT r.disqualified
        AND r.buy_in = 0
    """,
        {"tournament_id": tournament_id},
    )[0][0]

    buy_in_results = db(
        """
        SELECT
            a.name,
            :buy_in_place as place_finish,
            CASE
                WHEN a.member = 0 THEN 0  -- Guests always get 0 points
                WHEN a.member = 1 THEN :last_place_points - 4  -- Member buy-ins: last place with fish - 4 points
                ELSE 0
            END as points,
            a.member
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        AND r.buy_in = 1
        AND NOT r.disqualified
        ORDER BY a.name
    """,
        {
            "tournament_id": tournament_id,
            "buy_in_place": buy_in_place,
            "last_place_points": last_place_with_fish_points,
        },
    )

    return templates.TemplateResponse(
        "tournament_results.html",
        {
            "request": request,
            "user": user,
            "tournament": tournament,
            "tournament_stats": tournament_stats,
            "team_results": team_results,
            "individual_results": individual_results,
            "buy_in_results": buy_in_results,
        },
    )


@router.get("/calendar")
async def calendar_page(request: Request):
    """Calendar page with dynamic event loading from database."""
    user = u(request)

    # Get current year and next year
    current_year = datetime.now().year
    next_year = current_year + 1

    # Function to get calendar data for a specific year
    def get_year_calendar_data(year):
        # Get all events from the events table (the authoritative source)
        # No longer using calendar_events table to avoid duplicates
        calendar_events = []  # Empty list since we're not using calendar_events table

        tournament_events = db(
            """
            SELECT e.id as event_id, e.date, e.name, e.event_type, e.description,
                   p.id as poll_id, p.title as poll_title, p.starts_at, p.closes_at, p.closed,
                   t.id as tournament_id, t.complete as tournament_complete
            FROM events e
            LEFT JOIN polls p ON e.id = p.event_id
            LEFT JOIN tournaments t ON e.id = t.event_id
            WHERE strftime('%Y', e.date) = :year
            ORDER BY e.date
        """,
            {"year": str(year)},
        )

        # Build calendar data structure with enhanced event info
        return build_calendar_data_with_polls(calendar_events, tournament_events, year)

    # Get data for both years
    current_calendar_data, current_event_details, current_event_types = get_year_calendar_data(
        current_year
    )
    next_calendar_data, next_event_details, next_event_types = get_year_calendar_data(next_year)

    # Combine event types from both years
    all_event_types = current_event_types | next_event_types

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
            "event_types_present": all_event_types,
        },
    )


def build_calendar_data_with_polls(calendar_events, tournament_events, year=2025):
    """Build calendar data structure with enhanced poll and tournament information."""
    # Set Sunday as the first day of the week to match US calendar convention
    calendar.setfirstweekday(calendar.SUNDAY)

    # Combine all events and store detailed event info
    all_events = {}
    event_details = {}  # Store detailed event info for modal display
    event_types_present = set()  # Track which event types exist

    # Add calendar events (event_date, title, event_type, description)
    for event in calendar_events:
        date_obj = datetime.strptime(event[0], "%Y-%m-%d")
        day = date_obj.day
        month = date_obj.month
        event_type = event[2]
        event_key = f"{month}-{day}"

        if month not in all_events:
            all_events[month] = {}
        if day not in all_events[month]:
            all_events[month][day] = []

        all_events[month][day].append({"type": event_type, "title": event[1]})
        event_types_present.add(event_type)

        # Store detailed event info
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

    # Add tournament events with poll/tournament information
    # tournament_events columns: event_id, date, name, event_type, description, poll_id, poll_title, starts_at, closes_at, closed, tournament_id, tournament_complete
    for event in tournament_events:
        date_obj = datetime.strptime(event[1], "%Y-%m-%d")  # event[1] is date
        day = date_obj.day
        month = date_obj.month
        event_key = f"{month}-{day}"
        event_type = event[3]  # event[3] is event_type

        if month not in all_events:
            all_events[month] = {}
        if day not in all_events[month]:
            all_events[month][day] = []

        all_events[month][day].append(
            {
                "type": event_type,
                "title": event[2],  # event[2] is name
            }
        )
        event_types_present.add(event_type)

        # Determine poll status for the event
        now = datetime.now().date()
        event_date = date_obj.date()
        poll_id = event[5]  # poll_id
        poll_closed = event[9]  # closed
        tournament_id = event[10]  # tournament_id
        tournament_complete = event[11]  # tournament_complete

        poll_status = None
        poll_link = None
        tournament_link = None

        if poll_id:
            if event_date > now:
                # Future event - check if poll is active
                if not poll_closed:
                    poll_status = "active"
                    poll_link = f"/polls#{poll_id}"
                else:
                    poll_status = "closed"
                    poll_link = f"/polls#{poll_id}"
            else:
                # Past event - show poll results
                poll_status = "results"
                poll_link = f"/polls#{poll_id}"

        # Add tournament results link if tournament exists and is complete
        if tournament_id and tournament_complete:
            # Always use local tournament view
            tournament_link = f"/tournaments/{tournament_id}"

        # Store detailed event info with poll and tournament links
        if event_key not in event_details:
            event_details[event_key] = []
        event_details[event_key].append(
            {
                "title": event[2],  # name
                "type": event_type,
                "description": event[4] if event[4] else "",  # description
                "date": event[1],  # date
                "event_id": event[0],  # event_id
                "poll_id": poll_id,
                "poll_status": poll_status,
                "poll_link": poll_link,
                "tournament_id": tournament_id,
                "tournament_complete": tournament_complete,
                "tournament_link": tournament_link,
            }
        )

    # Build the exact calendar structure expected by template
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
        # Get calendar for this month
        cal = calendar.monthcalendar(year, month_idx)

        # Build weeks structure
        weeks = []
        for week in cal:
            week_days = []
            for day in week:
                if day == 0:
                    week_days.append("")
                else:
                    day_str = str(day)

                    # Check if this day has events
                    if month_idx in all_events and day in all_events[month_idx]:
                        events_for_day = all_events[month_idx][day]

                        # Apply markers based on event types (prioritize SABC tournaments)
                        has_sabc = any(e["type"] == "sabc_tournament" for e in events_for_day)
                        has_meeting = False
                        has_holiday = any(e["type"] == "holiday" for e in events_for_day)
                        has_other = any(e["type"] == "other_tournament" for e in events_for_day)

                        if has_sabc:
                            day_str += "†"  # Blue marker for SABC tournaments
                        elif has_meeting:
                            day_str += "§"  # Green marker for SABC meetings
                        elif has_other:
                            day_str += "‡"  # Orange marker for other tournaments
                        elif has_holiday:
                            day_str += "*"  # Red marker for holidays

                    week_days.append(day_str)

            weeks.append(week_days)

        calendar_structure.append([month_name, weeks])

    return calendar_structure, event_details, event_types_present


@router.get("/home-paginated")
async def home_paginated(request: Request, page: int = 1):
    user = u(request)
    items_per_page = 4  # Show 4 tournament cards per page
    offset = (page - 1) * items_per_page

    # Get all tournaments with event data for display
    # Tournament results are truncated, so we'll get the first few results
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

    # Get total count for pagination
    total_tournaments = db("SELECT COUNT(*) FROM tournaments")[0][0]
    total_pages = (total_tournaments + items_per_page - 1) // items_per_page

    # Get latest news items for sidebar
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

    # Enhance tournament data with top results
    tournaments_with_results = []
    for tournament in tournaments:
        tournament_id = tournament[0]

        # Get top 3 team results for this tournament
        top_results = db(
            """
            SELECT
                ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place,
                a1.name as angler1_name,
                a2.name as angler2_name,
                tr.total_weight
            FROM team_results tr
            JOIN anglers a1 ON tr.angler1_id = a1.id
            JOIN anglers a2 ON tr.angler2_id = a2.id
            WHERE tr.tournament_id = :tournament_id
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

    # Calculate page range for pagination
    # Show up to 7 page numbers at a time
    window_size = 7
    if total_pages <= window_size:
        # Show all pages if total is less than window size
        page_range = list(range(1, total_pages + 1))
    else:
        # Calculate start and end of page range window
        half_window = window_size // 2

        # Center the window around current page
        if page <= half_window:
            # Near the beginning
            page_range = list(range(1, window_size + 1))
        elif page >= total_pages - half_window:
            # Near the end
            page_range = list(range(total_pages - window_size + 1, total_pages + 1))
        else:
            # In the middle
            page_range = list(range(page - half_window, page + half_window + 1))

    # Calculate start and end indices for display
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


@router.get("/awards")
@router.get("/awards/{year}")
async def awards(request: Request, year: Optional[int] = None):
    user = u(request)

    # Default to current year if none provided
    if year is None:
        year = datetime.now().year

    # Get all available years from events (only current year and past)
    current_year = datetime.now().year
    available_years = db(
        "SELECT DISTINCT year FROM events WHERE year IS NOT NULL AND year <= :year ORDER BY year DESC",
        {"year": current_year},
    )
    years = [row[0] for row in available_years]

    if not years:
        years = [datetime.now().year]

    # Ensure requested year is valid
    if year not in years:
        year = years[0]

    # Calculate Angler of the Year standings with dynamic points calculation
    aoy_query = """
        WITH tournament_standings AS (
            SELECT
                r.angler_id,
                r.tournament_id,
                r.total_weight - COALESCE(r.dead_fish_penalty, 0) as adjusted_weight,
                r.num_fish,
                r.disqualified,
                r.buy_in,
                DENSE_RANK() OVER (
                    PARTITION BY r.tournament_id
                    ORDER BY
                        CASE WHEN r.disqualified = 1 THEN 0 ELSE r.total_weight - COALESCE(r.dead_fish_penalty, 0) END DESC
                ) as place_finish,
                COUNT(*) OVER (PARTITION BY r.tournament_id) as total_participants
            FROM results r
            JOIN tournaments t ON r.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE e.year = :year
        ),
        points_calc AS (
            SELECT
                angler_id,
                tournament_id,
                adjusted_weight,
                num_fish,
                place_finish,
                CASE
                    WHEN disqualified = 1 THEN 0
                    ELSE 101 - place_finish
                END as points
            FROM tournament_standings
        )
        SELECT
            a.name,
            SUM(CASE WHEN a.member = 1 THEN pc.points ELSE 0 END) as total_points,
            SUM(pc.num_fish) as total_fish,
            SUM(pc.adjusted_weight) as total_weight,
            COUNT(DISTINCT pc.tournament_id) as events_fished
        FROM anglers a
        JOIN points_calc pc ON a.id = pc.angler_id
        WHERE a.member = 1
        GROUP BY a.id, a.name
        ORDER BY total_points DESC, total_weight DESC
    """

    aoy_standings = db(aoy_query, {"year": year})

    # Calculate Heavy Stringer (best single tournament weight)
    heavy_stringer_query = """
        SELECT
            a.name,
            r.total_weight,
            r.num_fish,
            (substr(e.date, 1, 4) || ' ' ||
             CASE substr(e.date, 6, 2)
                 WHEN '01' THEN 'January'
                 WHEN '02' THEN 'February'
                 WHEN '03' THEN 'March'
                 WHEN '04' THEN 'April'
                 WHEN '05' THEN 'May'
                 WHEN '06' THEN 'June'
                 WHEN '07' THEN 'July'
                 WHEN '08' THEN 'August'
                 WHEN '09' THEN 'September'
                 WHEN '10' THEN 'October'
                 WHEN '11' THEN 'November'
                 WHEN '12' THEN 'December'
             END || ' Tournament') as tournament_name,
            e.date
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        WHERE e.year = :year AND r.total_weight > 0
        ORDER BY r.total_weight DESC
        LIMIT 1
    """

    heavy_stringer = db(heavy_stringer_query, {"year": year})

    # Calculate Big Bass of the Year
    big_bass_query = """
        SELECT
            a.name,
            r.big_bass_weight,
            (substr(e.date, 1, 4) || ' ' ||
             CASE substr(e.date, 6, 2)
                 WHEN '01' THEN 'January'
                 WHEN '02' THEN 'February'
                 WHEN '03' THEN 'March'
                 WHEN '04' THEN 'April'
                 WHEN '05' THEN 'May'
                 WHEN '06' THEN 'June'
                 WHEN '07' THEN 'July'
                 WHEN '08' THEN 'August'
                 WHEN '09' THEN 'September'
                 WHEN '10' THEN 'October'
                 WHEN '11' THEN 'November'
                 WHEN '12' THEN 'December'
             END || ' Tournament') as tournament_name,
            e.date
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        WHERE e.year = :year AND r.big_bass_weight >= 5.0  -- Minimum 5 lbs per bylaws
        ORDER BY r.big_bass_weight DESC
        LIMIT 1
    """

    big_bass = db(big_bass_query, {"year": year})

    # Get tournament statistics for the year
    year_stats_query = """
        SELECT
            COUNT(DISTINCT t.id) as total_tournaments,
            COUNT(DISTINCT a.id) as unique_anglers,
            SUM(r.num_fish) as total_fish,
            SUM(r.total_weight) as total_weight,
            AVG(r.total_weight) as avg_weight
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        JOIN results r ON t.id = r.tournament_id
        JOIN anglers a ON r.angler_id = a.id
        WHERE e.year = :year
    """

    year_stats = db(year_stats_query, {"year": year})
    stats = year_stats[0] if year_stats else (0, 0, 0, 0.0, 0.0)

    ctx = {
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
    }

    return templates.TemplateResponse("awards.html", ctx)


@router.get("/health")
async def health_check():
    """Health check endpoint for CI/CD and monitoring."""
    try:
        # Test database connection
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


@router.get("/api/lakes")
async def api_get_lakes():
    """Get all lakes from lakes.yaml for dropdowns."""
    lakes_data = load_lakes_data()
    lakes = []
    for lake_key, lake_info in lakes_data.items():
        lakes.append(
            {
                "key": lake_key,
                "name": lake_info.get("display_name", lake_key.replace("_", " ").title()),
            }
        )
    return JSONResponse(sorted(lakes, key=lambda x: x["name"]))


@router.get("/api/lakes/{lake_key}/ramps")
async def api_get_lake_ramps(lake_key: str):
    """Get ramps for a specific lake."""
    lakes_data = load_lakes_data()
    if lake_key in lakes_data:
        ramps = lakes_data[lake_key].get("ramps", [])
        return JSONResponse({"ramps": ramps})
    return JSONResponse({"ramps": []})


# Catch-all route for static pages (must be last)
@router.get("/{page:path}")
async def page(request: Request, page: str = "", p: int = 1):
    user = u(request)
    if page in ["", "about", "bylaws", "awards"]:
        # Use home page for the root route
        if not page:
            return await home_paginated(request, p)

        # For other static pages, use simple template
        t = f"{page}.html"
        ctx = {"request": request, "user": user}
        return templates.TemplateResponse(t, ctx)
    # Return 404 for unknown pages
    raise HTTPException(status_code=404, detail="Page not found")
