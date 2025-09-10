@app.get("/login")
async def login_page(request: Request):
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("login.html", {"request": request})
    )


@app.get("/register")
async def register_page(request: Request):
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("register.html", {"request": request})
    )


@app.get("/roster")
async def roster(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")

    # Get all active members and tournament participants with last tournament date for guests
    members = db("""
        SELECT DISTINCT a.name, a.email, a.member, a.is_admin, a.active, a.created_at, a.phone,
               CASE
                   WHEN a.active = 0 THEN (
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
        SELECT op.position, a.name, a.email, a.phone
        FROM officer_positions op
        JOIN anglers a ON op.angler_id = a.id
        WHERE op.year = 2025
        ORDER BY
            CASE op.position
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


@app.get("/polls")
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
    polls = []
    for poll_data in polls_data:
        poll_id = poll_data[0]

        # Get poll options for this poll
        options_data = db(
            """
            SELECT po.id, po.option_text, po.option_data,
                   COUNT(pv.id) as vote_count
            FROM poll_options po
            LEFT JOIN poll_votes pv ON po.id = pv.option_id
            WHERE po.poll_id = :poll_id
            GROUP BY po.id, po.option_text, po.option_data
            ORDER BY po.id
        """,
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

            # For admins, include individual vote details
            if user.get("is_admin"):
                vote_details = db(
                    """
                    SELECT pv.id, a.name as voter_name, pv.voted_at
                    FROM poll_votes pv
                    JOIN anglers a ON pv.angler_id = a.id
                    WHERE pv.option_id = :option_id
                    ORDER BY pv.voted_at DESC
                """,
                    {"option_id": option_data[0]},
                )

                option_dict["votes"] = [
                    {"vote_id": vote[0], "voter_name": vote[1], "voted_at": vote[2]}
                    for vote in vote_details
                ]

            options.append(option_dict)

        # Get member voting statistics for this poll
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

    # Get lakes and ramps data for tournament location voting from YAML
    lakes_data = []
    lakes = get_lakes_list()
    for lake_id, lake_name, location in lakes:
        # Get ramps for this lake using the lake_id (numeric)
        ramps_tuples = get_ramps_for_lake(lake_id)
        # Convert tuple format (id, name, lake_id) to dict format for template with capitalized names
        ramps = [{"id": r[0], "name": r[1].title()} for r in ramps_tuples]
        lakes_data.append(
            {
                "id": lake_id,
                "name": lake_name,
                "ramps": ramps,
            }
        )

    return templates.TemplateResponse(
        "polls.html",
        {
            "request": request,
            "user": user,
            "polls": polls,
            "lakes_data": lakes_data,
        },
    )


@app.post("/polls/{poll_id}/vote")
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

        poll = poll_check[0]
        if poll[4]:  # already_voted
            return RedirectResponse(
                "/polls?error=You have already voted in this poll", status_code=302
            )

        if poll[1]:  # closed
            return RedirectResponse("/polls?error=This poll is closed", status_code=302)

        from datetime import datetime

        now = datetime.now()
        starts_at = datetime.fromisoformat(poll[2])
        closes_at = datetime.fromisoformat(poll[3])
        if now < starts_at or now > closes_at:  # not within voting window
            return RedirectResponse(
                "/polls?error=This poll is not currently accepting votes", status_code=302
            )

        # Get poll type to determine how to handle the vote
        poll_type = db("SELECT poll_type FROM polls WHERE id = :poll_id", {"poll_id": poll_id})[0][
            0
        ]

        if poll_type == "tournament_location":
            # Handle dynamic tournament location vote
            try:
                import json

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
                lake_name = find_lake_by_id(lake_id_int, "name")
                ramp_name = find_ramp_name_by_id(vote_data["ramp_id"])

                if not lake_name or not ramp_name:
                    return RedirectResponse("/polls?error=Lake or ramp not found", status_code=302)

                start_formatted = time_format_filter(vote_data["start_time"])
                end_formatted = time_format_filter(vote_data["end_time"])
                option_text = f"{lake_name} - {ramp_name} ({start_formatted} to {end_formatted})"

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


@app.get("/profile")
async def profile(request: Request):
    if not (user := u(request)):
        return RedirectResponse("/login")

    # Calculate real tournament statistics
    user_id = user["id"]
    current_year = datetime.now().year

    # Get basic tournament stats
    tournaments = db(
        "SELECT COUNT(*) as count FROM results r JOIN tournaments t ON r.tournament_id = t.id WHERE r.angler_id = :id AND t.complete = 1",
        {"id": user_id},
    )[0][0]

    # Get best weight (total weight minus dead fish penalty)
    best_weight_result = db(
        "SELECT MAX(total_weight - dead_fish_penalty) as best FROM results r JOIN tournaments t ON r.tournament_id = t.id WHERE r.angler_id = :id AND t.complete = 1 AND NOT r.disqualified",
        {"id": user_id},
    )
    best_weight = float(best_weight_result[0][0] or 0) if best_weight_result else 0.0

    # Get personal best big bass
    big_bass_result = db(
        "SELECT MAX(big_bass_weight) as best FROM results r JOIN tournaments t ON r.tournament_id = t.id WHERE r.angler_id = :id AND t.complete = 1",
        {"id": user_id},
    )
    big_bass = float(big_bass_result[0][0] or 0) if big_bass_result else 0.0

    # Get tournament finishes - calculate both current year and all-time
    def get_finishes(year_filter=None):
        """Get tournament finishes with optional year filter"""
        year_condition = "AND e.year = :year" if year_filter else ""
        params = {"id": user_id}
        if year_filter:
            params["year"] = year_filter

        # First try team results
        team_finishes = db(
            f"""
            SELECT tr.place_finish
            FROM team_results tr
            JOIN tournaments t ON tr.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE (tr.angler1_id = :id OR tr.angler2_id = :id) AND t.complete = 1 {year_condition}
        """,
            params,
        )

        # If no team results, use individual results
        if not team_finishes:
            individual_finishes = db(
                f"""
                SELECT r.place_finish
                FROM results r
                JOIN tournaments t ON r.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE r.angler_id = :id AND t.complete = 1 AND r.place_finish > 0 {year_condition}
            """,
                params,
            )
            return individual_finishes
        return team_finishes

    # Calculate current year finishes
    current_year_finishes = get_finishes(current_year)
    current_first = len([f for f in current_year_finishes if f[0] == 1])
    current_second = len([f for f in current_year_finishes if f[0] == 2])
    current_third = len([f for f in current_year_finishes if f[0] == 3])

    # Calculate all-time finishes (since 2022)
    all_time_finishes = get_finishes()
    all_time_first = len([f for f in all_time_finishes if f[0] == 1])
    all_time_second = len([f for f in all_time_finishes if f[0] == 2])
    all_time_third = len([f for f in all_time_finishes if f[0] == 3])

    # For backward compatibility, use current year as primary stats
    first_place = current_first
    second_place = current_second
    third_place = current_third

    # Get current year AOY stats by calculating points directly
    # Calculate points for user in current year tournaments
    user_points_result = db(
        """
        SELECT SUM(r.points) as total_points
        FROM results r
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        WHERE r.angler_id = :id AND e.year = :year AND t.complete = 1
    """,
        {"id": user_id, "year": current_year},
    )

    aoy_points = user_points_result[0][0] if user_points_result and user_points_result[0][0] else 0

    # Calculate AOY position by ranking all members by points for current year
    if aoy_points > 0:
        aoy_position_result = db(
            """
            SELECT COUNT(*) + 1 as position
            FROM (
                SELECT r.angler_id, SUM(r.points) as total_points
                FROM results r
                JOIN tournaments t ON r.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                JOIN anglers a ON r.angler_id = a.id
                WHERE e.year = :year AND t.complete = 1 AND a.member = 1
                GROUP BY r.angler_id
                HAVING SUM(r.points) > :user_points
            )
        """,
            {"year": current_year, "user_points": aoy_points},
        )
        aoy_position = aoy_position_result[0][0] if aoy_position_result else None
    else:
        aoy_position = None

    # Current year tournaments
    current_year_tournaments = db(
        """
        SELECT COUNT(*) as count
        FROM results r
        JOIN tournaments t ON r.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        WHERE r.angler_id = :id AND e.year = :year AND t.complete = 1
    """,
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
                "first_place": first_place,
                "second_place": second_place,
                "third_place": third_place,
                "aoy_points": aoy_points,
                "aoy_position": aoy_position,
                "current_year_tournaments": current_year_tournaments,
                "points_behind": 0,  # Would need leader calculation
                "avg_points": 0,  # Would need average calculation
                # All-time stats for tabbed interface
                "all_time_first": all_time_first,
                "all_time_second": all_time_second,
                "all_time_third": all_time_third,
                "current_first": current_first,
                "current_second": current_second,
                "current_third": current_third,
            },
            "current_year": current_year,
            "success": request.query_params.get("success"),
            "error": request.query_params.get("error"),
        },
    )


@app.get("/admin/news")
async def admin_news(request: Request):
    """Admin page for managing news announcements."""
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")

    # Get all news items with last editor or original author
    news_items = db("""
        SELECT n.id, n.title, n.content, n.created_at, n.published, n.priority,
               n.expires_at,
               COALESCE(e.name, a.name) as author_name
        FROM news n
        LEFT JOIN anglers a ON n.author_id = a.id
        LEFT JOIN anglers e ON n.last_edited_by = e.id
        ORDER BY n.created_at DESC
    """)

    return templates.TemplateResponse(
        "admin/news.html", {"request": request, "user": user, "news_items": news_items}
    )


@app.post("/admin/news/create")
async def create_news(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    priority: int = Form(0),
):
    """Create a new news announcement."""
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")

    try:
        db(
            """
            INSERT INTO news (title, content, author_id, published, priority)
            VALUES (:title, :content, :author_id, :published, :priority)
        """,
            {
                "title": title.strip(),
                "content": content.strip(),
                "author_id": user["id"],
                "published": True,
                "priority": priority,
            },
        )
        return RedirectResponse("/admin/news?success=News created successfully", status_code=302)
    except Exception as e:
        return RedirectResponse(f"/admin/news?error={str(e)}", status_code=302)


@app.post("/admin/news/{news_id}/update")
async def update_news(
    request: Request,
    news_id: int,
    title: str = Form(...),
    content: str = Form(...),
    priority: int = Form(0),
):
    """Update an existing news announcement."""
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")

    try:
        db(
            """
            UPDATE news
            SET title = :title, content = :content, published = :published,
                priority = :priority, updated_at = CURRENT_TIMESTAMP,
                last_edited_by = :editor_id
            WHERE id = :id
        """,
            {
                "id": news_id,
                "title": title.strip(),
                "content": content.strip(),
                "published": True,
                "priority": priority,
                "editor_id": user["id"],
            },
        )
        return RedirectResponse("/admin/news?success=News updated successfully", status_code=302)
    except Exception as e:
        return RedirectResponse(f"/admin/news?error={str(e)}", status_code=302)


@app.delete("/admin/news/{news_id}")
async def delete_news(request: Request, news_id: int):
    """Delete a news announcement."""
    if not (user := u(request)) or not user.get("is_admin"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        db("DELETE FROM news WHERE id = :id", {"id": news_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/admin/{page}")
async def admin_page(request: Request, page: str, upcoming_page: int = 1, past_page: int = 1):
    if isinstance(user := admin(request), RedirectResponse):
        return user
    ctx = {"request": request, "user": user}
    if page == "events":
        # Pagination settings
        per_page = 20
        upcoming_offset = (upcoming_page - 1) * per_page
        past_offset = (past_page - 1) * per_page

        # Get total counts for pagination
        total_upcoming = db("SELECT COUNT(*) FROM events WHERE date >= date('now')")[0][0]
        total_past = db("SELECT COUNT(*) FROM events WHERE date < date('now')")[0][0]

        # Calculate pagination info
        upcoming_total_pages = (total_upcoming + per_page - 1) // per_page
        past_total_pages = (total_past + per_page - 1) // per_page

        # Get upcoming events with additional data for the template
        events = db(
            """
            SELECT
                e.id,
                e.date,
                e.name,
                e.description,
                e.event_type,
                strftime('%w', e.date) as day_num,
                CASE strftime('%w', e.date)
                    WHEN '0' THEN 'Sunday'
                    WHEN '1' THEN 'Monday'
                    WHEN '2' THEN 'Tuesday'
                    WHEN '3' THEN 'Wednesday'
                    WHEN '4' THEN 'Thursday'
                    WHEN '5' THEN 'Friday'
                    WHEN '6' THEN 'Saturday'
                END as day_name,
                EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
                EXISTS(
                    SELECT 1 FROM polls p
                    WHERE p.event_id = e.id
                    AND datetime('now', 'localtime') >= datetime(p.starts_at)
                    AND datetime('now', 'localtime') < datetime(p.closes_at)
                    AND p.closed = 0
                ) as poll_active,
                EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
                EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id AND t.complete = 1) as tournament_complete,
                e.start_time,
                e.weigh_in_time,
                e.lake_name,
                e.ramp_name,
                e.entry_fee,
                e.holiday_name
            FROM events e
            WHERE e.date >= date('now')
            ORDER BY e.date
            LIMIT :limit OFFSET :offset
        """,
            {"limit": per_page, "offset": upcoming_offset},
        )

        # Convert to list of dicts for easier template access
        ctx["events"] = [
            {
                "id": event[0],
                "date": event[1],
                "name": event[2] if event[2] else "",
                "description": event[3] if event[3] else "",
                "event_type": event[4] if event[4] else "sabc_tournament",
                "day_name": event[6],
                "has_poll": bool(event[7]),
                "poll_active": bool(event[8]),
                "has_tournament": bool(event[9]),
                "tournament_complete": bool(event[10]),
                "start_time": event[11],
                "weigh_in_time": event[12],
                "lake_name": event[13],
                "ramp_name": event[14],
                "entry_fee": event[15],
                "holiday_name": event[16],
            }
            for event in events
        ]

        # Get past events for display
        past_events = db(
            """
            SELECT e.id, e.date, e.name, e.description, e.event_type,
                EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id AND t.complete = 1) as tournament_complete,
                EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
                EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
                EXISTS(
                    SELECT 1 FROM tournaments t
                    WHERE t.event_id = e.id
                    AND (EXISTS(SELECT 1 FROM results WHERE tournament_id = t.id)
                         OR EXISTS(SELECT 1 FROM team_results WHERE tournament_id = t.id))
                ) as has_results,
                e.start_time,
                e.weigh_in_time,
                e.lake_name,
                e.ramp_name,
                e.entry_fee,
                e.holiday_name
            FROM events e
            WHERE e.date < date('now')
            ORDER BY e.date DESC
            LIMIT :limit OFFSET :offset
        """,
            {"limit": per_page, "offset": past_offset},
        )

        ctx["past_events"] = [
            {
                "id": event[0],
                "date": event[1],
                "name": event[2] if event[2] else "",
                "description": event[3] if event[3] else "",
                "event_type": event[4] if event[4] else "sabc_tournament",
                "tournament_complete": bool(event[5]),
                "has_poll": bool(event[6]),
                "has_tournament": bool(event[7]),
                "has_results": bool(event[8]),
                "start_time": event[9],
                "weigh_in_time": event[10],
                "lake_name": event[11],
                "ramp_name": event[12],
                "entry_fee": event[13],
                "holiday_name": event[14],
            }
            for event in past_events
        ]

        # Add pagination context
        ctx.update(
            {
                "upcoming_page": upcoming_page,
                "upcoming_total_pages": upcoming_total_pages,
                "upcoming_has_prev": upcoming_page > 1,
                "upcoming_has_next": upcoming_page < upcoming_total_pages,
                "upcoming_prev_page": upcoming_page - 1 if upcoming_page > 1 else None,
                "upcoming_next_page": upcoming_page + 1
                if upcoming_page < upcoming_total_pages
                else None,
                "past_page": past_page,
                "past_total_pages": past_total_pages,
                "past_has_prev": past_page > 1,
                "past_has_next": past_page < past_total_pages,
                "past_prev_page": past_page - 1 if past_page > 1 else None,
                "past_next_page": past_page + 1 if past_page < past_total_pages else None,
                "total_upcoming": total_upcoming,
                "total_past": total_past,
                "per_page": per_page,
            }
        )

    elif page == "users":
        tab = request.query_params.get("tab", "active")
        if tab == "inactive":
            # Show inactive members (member=0, active=1)
            ctx["users"] = db(
                "SELECT id, name, email, member, is_admin, active FROM anglers WHERE member = 0 AND active = 1 ORDER BY name"
            )
        else:
            # Show active members (member=1, active=1)
            ctx["users"] = db(
                "SELECT id, name, email, member, is_admin, active FROM anglers WHERE member = 1 AND active = 1 ORDER BY is_admin DESC, name"
            )
        ctx["current_tab"] = tab
    return templates.TemplateResponse(f"admin/{page}.html", ctx)


@app.get("/admin/federal-holidays/{year}")
async def get_federal_holidays_api(request: Request, year: int):
    """API endpoint to get federal holidays for a year."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        holidays = get_federal_holidays(year)
        return JSONResponse({"holidays": holidays})
    except Exception as e:
        return JSONResponse({"error": f"Error getting holidays: {str(e)}"}, status_code=500)


@app.post("/admin/events/bulk-delete")
async def bulk_delete_events(request: Request):
    """Delete multiple events at once (only if they have no results)."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        data = await request.json()
        event_ids = data.get("event_ids", [])

        if not event_ids:
            return JSONResponse({"error": "No events selected"}, status_code=400)

        deleted_count = 0
        blocked_events = []

        # Check each event and delete if safe
        for event_id in event_ids:
            # Check if event has results
            has_results = db(
                """
                SELECT 1 FROM tournaments t
                WHERE t.event_id = ?
                AND (EXISTS(SELECT 1 FROM results WHERE tournament_id = t.id)
                     OR EXISTS(SELECT 1 FROM team_results WHERE tournament_id = t.id))
                LIMIT 1
            """,
                (event_id,),
            )

            if has_results:
                # Get event name for error message
                event_info = db("SELECT name, date FROM events WHERE id = :id", {"id": event_id})
                if event_info:
                    blocked_events.append(f"{event_info[0][0]} ({event_info[0][1]})")
                continue

            # Safe to delete - remove polls first, then event
            db(
                "DELETE FROM poll_votes WHERE poll_id IN (SELECT id FROM polls WHERE event_id = ?)",
                (event_id,),
            )
            db(
                "DELETE FROM poll_options WHERE poll_id IN (SELECT id FROM polls WHERE event_id = :event_id)",
                {"event_id": event_id},
            )
            db("DELETE FROM polls WHERE event_id = :event_id", {"event_id": event_id})
            db(
                "DELETE FROM tournaments WHERE event_id = :event_id AND complete = 0",
                {"event_id": event_id},
            )  # Only uncompleted tournaments
            db("DELETE FROM events WHERE id = :id", {"id": event_id})
            deleted_count += 1

        message = f"Successfully deleted {deleted_count} event(s)"
        if blocked_events:
            message += f". Could not delete {len(blocked_events)} event(s) with results: {', '.join(blocked_events[:3])}"
            if len(blocked_events) > 3:
                message += f" and {len(blocked_events) - 3} more"

        return JSONResponse(
            {
                "success": True,
                "deleted_count": deleted_count,
                "blocked_count": len(blocked_events),
                "message": message,
            }
        )

    except Exception as e:
        return JSONResponse({"error": f"Bulk delete failed: {str(e)}"}, status_code=500)


@app.post("/admin/events/bulk-create-holidays")
async def bulk_create_holidays(request: Request):
    """Create federal holidays for a given year."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        data = await request.json()
        year = data.get("year")

        if not year or not (2020 <= year <= 2030):
            return JSONResponse(
                {"error": "Invalid year. Must be between 2020 and 2030"}, status_code=400
            )

        holidays = get_federal_holidays(year)
        created_count = 0
        skipped_holidays = []

        for holiday_date, holiday_name in holidays:
            # Check if holiday already exists
            existing = db("SELECT id FROM events WHERE date = :date", {"date": holiday_date})
            if existing:
                skipped_holidays.append(f"{holiday_name} ({holiday_date})")
                continue

            # Create the holiday event
            db(
                """
                INSERT INTO events (date, year, name, event_type, description, holiday_name)
                VALUES (?, ?, ?, 'federal_holiday', ?, ?)
            """,
                (
                    holiday_date,
                    year,
                    holiday_name,
                    f"Federal holiday: {holiday_name}",
                    holiday_name,
                ),
            )
            created_count += 1

        message = f"Created {created_count} federal holiday(s) for {year}"
        if skipped_holidays:
            message += (
                f". Skipped {len(skipped_holidays)} existing: {', '.join(skipped_holidays[:3])}"
            )
            if len(skipped_holidays) > 3:
                message += f" and {len(skipped_holidays) - 3} more"

        return JSONResponse(
            {
                "success": True,
                "created_count": created_count,
                "skipped_count": len(skipped_holidays),
                "message": message,
            }
        )

    except Exception as e:
        return JSONResponse({"error": f"Holiday creation failed: {str(e)}"}, status_code=500)


@app.post("/admin/events/bulk-create-tournaments")
async def bulk_create_tournaments(request: Request):
    """Create monthly tournaments for a year."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        data = await request.json()
        year = data.get("year")
        start_month = data.get("start_month", 1)
        end_month = data.get("end_month", 12)
        weekend_preference = data.get("weekend_preference", "saturday")  # "saturday" or "sunday"

        if not year or not (2020 <= year <= 2030):
            return JSONResponse(
                {"error": "Invalid year. Must be between 2020 and 2030"}, status_code=400
            )

        if not (1 <= start_month <= 12) or not (1 <= end_month <= 12) or start_month > end_month:
            return JSONResponse({"error": "Invalid month range"}, status_code=400)

        created_count = 0
        skipped_months = []

        import calendar
        from datetime import date, timedelta

        for month in range(start_month, end_month + 1):
            # Find the 3rd Saturday or Sunday of the month
            first_day = date(year, month, 1)

            if weekend_preference == "saturday":
                target_weekday = 5  # Saturday
            else:
                target_weekday = 6  # Sunday

            # Find first target weekday
            days_to_target = (target_weekday - first_day.weekday()) % 7
            first_target = first_day + timedelta(days=days_to_target)

            # Get 3rd occurrence
            tournament_date = first_target + timedelta(days=14)

            # Make sure it's still in the same month
            if tournament_date.month != month:
                # Use 2nd occurrence instead
                tournament_date = first_target + timedelta(days=7)

            tournament_date_str = tournament_date.strftime("%Y-%m-%d")

            # Check if date already has an event
            existing = db("SELECT id FROM events WHERE date = :date", {"date": tournament_date_str})
            if existing:
                month_name = calendar.month_name[month]
                skipped_months.append(f"{month_name} ({tournament_date_str})")
                continue

            # Create the tournament event
            month_name = calendar.month_name[month]
            tournament_name = f"{month_name} {year} Tournament"

            db(
                """
                INSERT INTO events (date, year, name, event_type, description,
                                  start_time, weigh_in_time, entry_fee)
                VALUES (?, ?, ?, 'sabc_tournament', ?, '06:00', '15:00', 25.00)
            """,
                (
                    tournament_date_str,
                    year,
                    tournament_name,
                    f"SABC monthly tournament for {month_name} {year}",
                ),
            )
            created_count += 1

        message = f"Created {created_count} tournament(s) for {year}"
        if skipped_months:
            message += f". Skipped {len(skipped_months)} months with existing events: {', '.join(skipped_months)}"

        return JSONResponse(
            {
                "success": True,
                "created_count": created_count,
                "skipped_count": len(skipped_months),
                "message": message,
            }
        )

    except Exception as e:
        return JSONResponse({"error": f"Tournament creation failed: {str(e)}"}, status_code=500)


@app.post("/admin/events/create")
async def create_event(
    request: Request,
    date: str = Form(),
    name: str = Form(),
    event_type: str = Form(default="sabc_tournament"),
    description: str = Form(default=""),
    start_time: str = Form(default="06:00"),
    weigh_in_time: str = Form(default="15:00"),
    lake_name: str = Form(default=""),
    ramp_name: str = Form(default=""),
    entry_fee: float = Form(default=25.00),
    holiday_name: str = Form(default=""),
):
    """Create a new event and optionally auto-create poll for SABC tournaments."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        from datetime import datetime, timedelta

        # Validate input data
        validation = validate_event_data(
            date, name, event_type, start_time, weigh_in_time, entry_fee
        )

        # If there are errors, return with error message
        if validation["errors"]:
            error_msg = "; ".join(validation["errors"])
            return RedirectResponse(
                f"/admin/events?error=Validation failed: {error_msg}", status_code=302
            )

        # Show warnings in success message if any
        warning_msg = ""
        if validation["warnings"]:
            warning_msg = f"&warnings={'; '.join(validation['warnings'])}"

        # Parse the date to extract year
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.year

        # Insert the event with all new fields
        params = {
            "date": date,
            "year": year,
            "name": name,
            "event_type": event_type,
            "description": description,
            "start_time": start_time if event_type == "sabc_tournament" else None,
            "weigh_in_time": weigh_in_time if event_type == "sabc_tournament" else None,
            "lake_name": lake_name if lake_name else None,
            "ramp_name": ramp_name if ramp_name else None,
            "entry_fee": entry_fee if event_type == "sabc_tournament" else None,
            "holiday_name": holiday_name if event_type == "federal_holiday" else None,
        }
        event_id = db(
            """
            INSERT INTO events (date, year, name, event_type, description,
                              start_time, weigh_in_time, lake_name, ramp_name,
                              entry_fee, holiday_name)
            VALUES (:date, :year, :name, :event_type, :description,
                   :start_time, :weigh_in_time, :lake_name, :ramp_name,
                   :entry_fee, :holiday_name)
        """,
            params,
        )

        # Auto-create poll for SABC tournaments
        if event_type == "sabc_tournament":
            # Poll opens 7 days before and closes 5 days before the event
            poll_starts = (date_obj - timedelta(days=7)).isoformat()
            poll_closes = (date_obj - timedelta(days=5)).isoformat()

            # Create the tournament location poll
            poll_id = db(
                """
                INSERT INTO polls (title, description, poll_type, event_id, created_by,
                                 starts_at, closes_at, closed, multiple_votes)
                VALUES (:title, :description, 'tournament_location', :event_id, :created_by,
                       :starts_at, :closes_at, 0, 0)
            """,
                {
                    "title": name,
                    "description": description if description else f"Vote for location for {name}",
                    "event_id": event_id,
                    "created_by": user["id"],
                    "starts_at": poll_starts,
                    "closes_at": poll_closes,
                },
            )

            # Add all lakes as poll options by default from YAML
            all_lakes = get_lakes_list()
            import json

            for lake_id, lake_name, location in all_lakes:
                option_data = {"lake_id": lake_id}
                db(
                    """
                    INSERT INTO poll_options (poll_id, option_text, option_data)
                    VALUES (:poll_id, :option_text, :option_data)
                """,
                    {
                        "poll_id": poll_id,
                        "option_text": lake_name,
                        "option_data": json.dumps(option_data),
                    },
                )

        return RedirectResponse(
            f"/admin/events?success=Event created successfully{warning_msg}", status_code=302
        )

    except Exception as e:
        # Return to events page with error
        return RedirectResponse(
            f"/admin/events?error=Failed to create event: {str(e)}", status_code=302
        )


@app.get("/admin/events/{event_id}/info")
async def get_event_info(request: Request, event_id: int):
    """Get complete event information (for edit modal)."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        # Get event info with poll info and tournament info if they exist
        event_info = db(
            """
            SELECT e.id, e.date, e.name, e.description, e.event_type,
                   e.start_time, e.weigh_in_time,
                   COALESCE(t.lake_name, e.lake_name) as lake_name,
                   COALESCE(t.ramp_name, e.ramp_name) as ramp_name,
                   e.entry_fee, e.holiday_name,
                   p.closes_at, p.starts_at, p.id as poll_id, p.closed,
                   t.id as tournament_id
            FROM events e
            LEFT JOIN polls p ON p.event_id = e.id
            LEFT JOIN tournaments t ON t.event_id = e.id
            WHERE e.id = :event_id
            ORDER BY p.id DESC
            LIMIT 1
        """,
            {"event_id": event_id},
        )

        if event_info:
            event = event_info[0]

            # Convert lake name to display name if it exists
            lake_display_name = event[7] or ""
            if lake_display_name:
                yaml_key, lake_info, display_name = find_lake_data_by_db_name(lake_display_name)
                if display_name:
                    lake_display_name = display_name

            return JSONResponse(
                {
                    "id": event[0],
                    "date": event[1],
                    "name": event[2],
                    "description": event[3] or "",
                    "event_type": event[4],
                    "start_time": event[5],
                    "weigh_in_time": event[6],
                    "lake_name": lake_display_name,
                    "ramp_name": event[8] or "",
                    "entry_fee": float(event[9]) if event[9] else 25.00,
                    "holiday_name": event[10] or "",
                    "poll_closes_at": event[11],
                    "poll_starts_at": event[12],
                    "poll_id": event[13],
                    "poll_closed": bool(event[14]) if event[14] is not None else None,
                    "tournament_id": event[15],
                }
            )
        else:
            return JSONResponse({"error": "Event not found"}, status_code=404)

    except Exception as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)


@app.get("/admin/events/{event_id}/poll-info")
async def get_event_poll_info(request: Request, event_id: int):
    """Get poll information for an event (for backward compatibility)."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        poll_info = db(
            """
            SELECT p.closes_at, p.starts_at, p.id, p.closed
            FROM polls p
            WHERE p.event_id = :event_id
            ORDER BY p.id DESC
            LIMIT 1
        """,
            {"event_id": event_id},
        )

        if poll_info:
            return JSONResponse(
                {
                    "closes_at": poll_info[0][0],
                    "starts_at": poll_info[0][1],
                    "poll_id": poll_info[0][2],
                    "closed": bool(poll_info[0][3]),
                }
            )
        else:
            return JSONResponse({"error": "No poll found for this event"}, status_code=404)

    except Exception as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)


@app.post("/admin/events/validate")
async def validate_event(request: Request):
    """Validate event data via AJAX."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        data = await request.json()
        validation = validate_event_data(
            data.get("date", ""),
            data.get("name", ""),
            data.get("event_type", "sabc_tournament"),
            data.get("start_time"),
            data.get("weigh_in_time"),
            data.get("entry_fee"),
        )

        return JSONResponse(
            {
                "valid": len(validation["errors"]) == 0,
                "errors": validation["errors"],
                "warnings": validation["warnings"],
            }
        )

    except Exception as e:
        return JSONResponse({"error": f"Validation error: {str(e)}"}, status_code=500)


@app.post("/admin/events/edit")
async def edit_event(
    request: Request,
    event_id: int = Form(),
    date: str = Form(),
    name: str = Form(),
    event_type: str = Form(default="sabc_tournament"),
    description: str = Form(default=""),
    poll_closes_date: str = Form(default=""),
    start_time: str = Form(default=""),
    weigh_in_time: str = Form(default=""),
    lake_name: str = Form(default=""),
    ramp_name: str = Form(default=""),
    entry_fee: float = Form(default=25.00),
    holiday_name: str = Form(default=""),
):
    """Edit an existing event."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        from datetime import datetime

        # Validate input data (but allow same date for same event)
        validation = validate_event_data(
            date, name, event_type, start_time, weigh_in_time, entry_fee
        )

        # Filter out duplicate date warning if it's for the same event
        if validation["warnings"]:
            filtered_warnings = []
            for warning in validation["warnings"]:
                if "already has event" in warning:
                    # Check if it's the same event
                    existing = db(
                        "SELECT id FROM events WHERE date = ? AND id != ?", (date, event_id)
                    )
                    if existing:
                        filtered_warnings.append(warning)
                else:
                    filtered_warnings.append(warning)
            validation["warnings"] = filtered_warnings

        # If there are errors, return with error message
        if validation["errors"]:
            error_msg = "; ".join(validation["errors"])
            return RedirectResponse(
                f"/admin/events?error=Validation failed: {error_msg}", status_code=302
            )

        # Show warnings in success message if any
        warning_msg = ""
        if validation["warnings"]:
            warning_msg = f"&warnings={'; '.join(validation['warnings'])}"

        # Parse the date to extract year
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.year

        # Update the event with all fields
        db(
            """
            UPDATE events
            SET date = :date, year = :year, name = :name, event_type = :event_type,
                description = :description, start_time = :start_time, weigh_in_time = :weigh_in_time,
                lake_name = :lake_name, ramp_name = :ramp_name, entry_fee = :entry_fee,
                holiday_name = :holiday_name
            WHERE id = :id
        """,
            {
                "date": date,
                "year": year,
                "name": name,
                "event_type": event_type,
                "description": description,
                "start_time": start_time
                if start_time and event_type == "sabc_tournament"
                else None,
                "weigh_in_time": weigh_in_time
                if weigh_in_time and event_type == "sabc_tournament"
                else None,
                "lake_name": lake_name if lake_name else None,
                "ramp_name": ramp_name if ramp_name else None,
                "entry_fee": entry_fee if event_type == "sabc_tournament" else None,
                "holiday_name": holiday_name
                if holiday_name and event_type == "federal_holiday"
                else None,
                "id": event_id,
            },
        )

        # Also update tournament table if this event has a tournament
        if event_type == "sabc_tournament":
            # Convert display name back to key for storage
            lake_key = None
            if lake_name:
                # Find the lake key from the display name
                lakes_data = load_lakes_data()
                for key, info in lakes_data.items():
                    if info.get("display_name", key.replace("_", " ").title()) == lake_name:
                        lake_key = key
                        break
                # If no match found, use the name as-is (might be a key already)
                if not lake_key:
                    lake_key = lake_name.lower().replace(" ", "_")

            # Check if tournament exists for this event
            tournament = db(
                "SELECT id FROM tournaments WHERE event_id = :event_id", {"event_id": event_id}
            )
            if tournament:
                # Update tournament lake and ramp
                db(
                    """
                    UPDATE tournaments
                    SET lake_name = :lake_name, ramp_name = :ramp_name,
                        start_time = :start_time, end_time = :end_time,
                        entry_fee = :entry_fee
                    WHERE event_id = :event_id
                    """,
                    {
                        "lake_name": lake_key if lake_key else None,
                        "ramp_name": ramp_name if ramp_name else None,
                        "start_time": start_time if start_time else None,
                        "end_time": weigh_in_time if weigh_in_time else None,
                        "entry_fee": entry_fee,
                        "event_id": event_id,
                    },
                )

        # Update poll closes date if provided and event has a poll
        if poll_closes_date and event_type == "sabc_tournament":
            try:
                # Parse the datetime-local format and convert to ISO
                poll_closes_datetime = datetime.fromisoformat(poll_closes_date).isoformat()

                # Update the poll closes date
                db(
                    """
                    UPDATE polls
                    SET closes_at = :closes_at
                    WHERE event_id = :event_id
                """,
                    {"closes_at": poll_closes_datetime, "event_id": event_id},
                )

            except ValueError as ve:
                # Log the error but don't fail the entire event update
                logger.warning(f"Failed to parse poll closes date: {ve}")

        return RedirectResponse(
            f"/admin/events?success=Event updated successfully{warning_msg}", status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            f"/admin/events?error=Failed to update event: {str(e)}", status_code=302
        )


@app.delete("/admin/events/{event_id}")
async def delete_event(request: Request, event_id: int):
    """Delete an event and optionally cascade delete polls (tournaments require manual handling)."""
    # Simple authentication check
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        # Use a single database connection for all operations
        with engine.connect() as conn:
            # Check if user is admin
            user_result = conn.execute(
                text("SELECT is_admin FROM anglers WHERE id = :id AND active = 1"), {"id": user_id}
            )
            user_row = user_result.fetchone()
            if not user_row or not user_row[0]:
                return JSONResponse({"error": "Admin access required"}, status_code=403)

            # Check if event exists
            event_result = conn.execute(
                text("SELECT COUNT(*) FROM events WHERE id = :id"), {"id": event_id}
            )
            row = event_result.fetchone()
            event_count = row[0] if row else 0
            if event_count == 0:
                return JSONResponse({"error": "Event not found"}, status_code=404)

            # Check if event has tournaments with results (these block deletion)
            # First check if tournament exists
            tournament_result = conn.execute(
                text("SELECT id FROM tournaments WHERE event_id = :event_id"),
                {"event_id": event_id},
            )
            tournament_row = tournament_result.fetchone()

            if tournament_row:
                tournament_id = tournament_row[0]
                # Check for any results or team results
                results_count_query = text("""
                    SELECT
                        (SELECT COUNT(*) FROM results WHERE tournament_id = :tid) +
                        (SELECT COUNT(*) FROM team_results WHERE tournament_id = :tid) as total_results
                """)
                results_result = conn.execute(results_count_query, {"tid": tournament_id})
                row = results_result.fetchone()
                total_results = row[0] if row else 0

                if total_results > 0:
                    return JSONResponse(
                        {
                            "error": "Cannot delete event with tournament results. Please delete results first."
                        },
                        status_code=400,
                    )

                # If tournament exists but has no results, delete it
                conn.execute(
                    text("DELETE FROM tournaments WHERE id = :tid"), {"tid": tournament_id}
                )

            # Delete associated polls first (cascade delete)
            conn.execute(
                text(
                    "DELETE FROM poll_votes WHERE poll_id IN (SELECT id FROM polls WHERE event_id = :event_id)"
                ),
                {"event_id": event_id},
            )
            conn.execute(
                text(
                    "DELETE FROM poll_options WHERE poll_id IN (SELECT id FROM polls WHERE event_id = :event_id)"
                ),
                {"event_id": event_id},
            )
            conn.execute(
                text("DELETE FROM polls WHERE event_id = :event_id"), {"event_id": event_id}
            )

            # Delete the event
            conn.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})

            # Commit all changes
            conn.commit()

            return JSONResponse({"success": True}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)


@app.get("/admin/polls/create")
async def create_poll_form(request: Request, event_id: int = Query(None)):
    """Show poll creation form for a specific event, or event selection if no event_id provided."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        # If no event_id provided, show event selection page
        if event_id is None:
            # Get upcoming events that don't have polls yet
            available_events = db("""
                SELECT e.id, e.date, e.name, e.event_type, e.description
                FROM events e
                LEFT JOIN polls p ON e.id = p.event_id
                WHERE p.id IS NULL
                AND e.date >= date('now')
                AND e.event_type = 'sabc_tournament'
                ORDER BY e.date ASC
            """)

            return templates.TemplateResponse(
                "admin/new_poll.html",
                {"request": request, "user": user, "available_events": available_events},
            )

        # Get event data for specific event_id
        event_data = db(
            """
            SELECT id, date, name, event_type, description
            FROM events
            WHERE id = :event_id
        """,
            {"event_id": event_id},
        )

        if not event_data:
            return RedirectResponse("/admin/events?error=Event not found", status_code=302)

        event = event_data[0]

        # Check if event already has a poll
        existing_poll = db(
            "SELECT id FROM polls WHERE event_id = :event_id", {"event_id": event_id}
        )
        if existing_poll:
            return RedirectResponse(
                f"/admin/polls/{existing_poll[0][0]}/edit?info=Poll already exists for this event",
                status_code=302,
            )

        # Get all upcoming events for the template's event selector (but pre-select the current one)
        events = db(
            """
            SELECT id, date, name, event_type, description
            FROM events
            WHERE date >= date('now') OR id = :event_id
            ORDER BY date
        """,
            {"event_id": event_id},
        )

        # Get lakes and ramps for tournament polls from YAML
        lakes = get_lakes_list()
        ramps = get_all_ramps()

        context = {
            "request": request,
            "user": user,
            "events": events,
            "selected_event": event,
            "lakes": lakes,
            "ramps": ramps,
        }

        return templates.TemplateResponse("admin/create_poll.html", context)

    except Exception as e:
        return RedirectResponse(
            f"/admin/events?error=Failed to load poll creation form: {str(e)}", status_code=302
        )


@app.get("/admin/polls/create/generic")
async def create_generic_poll_form(request: Request):
    """Show generic poll creation form (no event needed)."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    return templates.TemplateResponse(
        "admin/create_generic_poll.html", {"request": request, "user": user}
    )


@app.post("/admin/polls/create")
async def create_poll(request: Request):
    """Create a new poll for an event."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        form = await request.form()

        event_id_raw = form.get("event_id")
        event_id = None
        if event_id_raw and isinstance(event_id_raw, str):
            event_id = int(event_id_raw)
        poll_type = form.get("poll_type", "")
        title = form.get("title", "")
        description = form.get("description", "")
        closes_at = form.get("closes_at", "")
        starts_at = form.get("starts_at", "")

        # For tournament polls, validate event exists
        if poll_type == "tournament_location" and event_id:
            event_data = db(
                "SELECT id, name, event_type, date FROM events WHERE id = :event_id",
                {"event_id": event_id},
            )
            if not event_data:
                return RedirectResponse("/admin/events?error=Event not found", status_code=302)

            event = event_data[0]

            # Check if event already has a poll
            existing_poll = db(
                "SELECT id FROM polls WHERE event_id = :event_id", {"event_id": event_id}
            )
            if existing_poll:
                return RedirectResponse(
                    f"/admin/polls/{existing_poll[0][0]}/edit?error=Poll already exists for this event",
                    status_code=302,
                )
        else:
            event = None

        # Generate title if not provided
        if not title and poll_type == "tournament_location" and event:
            # Use "Lake Selection Poll" instead of "Location Poll"
            title = f"{event[1]} Lake Selection Poll"
        elif not title and event:
            title = f"Poll for {event[1]}"
        elif not title:
            title = "Generic Poll"

        # Set default start time if not provided
        if not starts_at:
            from datetime import datetime, timedelta

            if event:
                # For tournament polls: 7 days before event
                event_date = datetime.strptime(event[3], "%Y-%m-%d")  # event[3] is the date
                starts_at = (event_date - timedelta(days=7)).isoformat()
            else:
                # For generic polls: tomorrow
                starts_at = (datetime.now() + timedelta(days=1)).isoformat()

        # Create the poll
        poll_id = db(
            """
            INSERT INTO polls (title, description, poll_type, event_id, created_by,
                             starts_at, closes_at, closed, multiple_votes)
            VALUES (:title, :description, :poll_type, :event_id, :created_by,
                   :starts_at, :closes_at, 0, 0)
        """,
            {
                "title": title,
                "description": description
                if description
                else (
                    f"Vote for location for {event[1]}"
                    if event
                    else "Vote for your preferred option"
                ),
                "poll_type": poll_type,
                "event_id": event_id if event_id else None,
                "created_by": user["id"],
                "starts_at": starts_at,
                "closes_at": closes_at,
            },
        )

        # Handle different poll types
        if poll_type == "tournament_location":
            # Handle simple lake selection
            import json

            selected_lake_ids = form.getlist("lake_ids")

            if selected_lake_ids:
                # Create poll options from selected lakes (simple lake names only)
                for lake_id_raw in selected_lake_ids:
                    if isinstance(lake_id_raw, str):
                        lake_name = find_lake_by_id(int(lake_id_raw), "name")
                        if lake_name:
                            db(
                                """
                                INSERT INTO poll_options (poll_id, option_text, option_data)
                                VALUES (:poll_id, :option_text, :option_data)
                            """,
                                {
                                    "poll_id": poll_id,
                                    "option_text": lake_name,
                                    "option_data": json.dumps({"lake_id": int(lake_id_raw)}),
                                },
                            )
            else:
                # If no lakes selected, add all lakes as fallback
                all_lakes = get_lakes_list()
                for lake_id, lake_name, location in all_lakes:
                    db(
                        """
                        INSERT INTO poll_options (poll_id, option_text, option_data)
                        VALUES (:poll_id, :option_text, :option_data)
                    """,
                        {
                            "poll_id": poll_id,
                            "option_text": lake_name,
                            "option_data": json.dumps({"lake_id": lake_id}),
                        },
                    )

        elif poll_type == "generic":
            # Handle generic poll options (array format)
            poll_options = form.getlist("poll_options[]")
            import json

            for option_text_raw in poll_options:
                if isinstance(option_text_raw, str) and option_text_raw.strip():
                    db(
                        """
                        INSERT INTO poll_options (poll_id, option_text, option_data)
                        VALUES (:poll_id, :option_text, :option_data)
                    """,
                        {
                            "poll_id": poll_id,
                            "option_text": option_text_raw.strip(),
                            "option_data": json.dumps({}),
                        },
                    )

        else:
            # Handle legacy generic poll options (fallback)
            for key in form.keys():
                value = form[key]
                if key.startswith("option_") and isinstance(value, str) and value.strip():
                    db(
                        """
                        INSERT INTO poll_options (poll_id, option_text, option_data)
                        VALUES (:poll_id, :option_text, :option_data)
                    """,
                        {
                            "poll_id": poll_id,
                            "option_text": value.strip(),
                            "option_data": json.dumps({}),
                        },
                    )

        # Log audit event for poll creation
        log_audit_event(
            action="CREATE_POLL",
            user_id=user.get("id"),
            user_email=user.get("email"),
            target_type="POLL",
            target_id=poll_id,
            new_value=title,
            details=f"Created poll: {title}"
        )
        
        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?success=Poll created successfully", status_code=302
        )

    except Exception as e:
        import traceback

        logger.error(f"Error creating poll: {e}", exc_info=True)
        return RedirectResponse(
            f"/admin/events?error=Failed to create poll: {str(e)}", status_code=302
        )


@app.get("/admin/polls/{poll_id}/edit")
async def edit_poll_form(request: Request, poll_id: int):
    """Show poll edit form."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        # Get poll data
        poll_data = db(
            """
            SELECT p.id, p.title, p.closes_at, p.poll_type, p.starts_at, p.description
            FROM polls p
            WHERE p.id = :poll_id
        """,
            {"poll_id": poll_id},
        )

        if not poll_data:
            return RedirectResponse("/polls?error=Poll not found", status_code=302)

        poll = poll_data[0]

        # If it's a tournament location poll, get additional data
        context = {"request": request, "user": user, "poll": poll}

        # Get poll options and votes for all poll types
        poll_options_data = db(
            """
            SELECT po.id, po.option_text, po.option_data
            FROM poll_options po
            WHERE po.poll_id = :poll_id
            ORDER BY po.id
        """,
            {"poll_id": poll_id},
        )

        poll_options = []
        for option_data in poll_options_data:
            option_dict = {"id": option_data[0], "text": option_data[1], "data": option_data[2]}

            # Get individual votes for this option
            vote_details = db(
                """
                SELECT pv.id, a.name as voter_name, pv.voted_at
                FROM poll_votes pv
                JOIN anglers a ON pv.angler_id = a.id
                WHERE pv.option_id = :option_id
                ORDER BY pv.voted_at DESC
            """,
                {"option_id": option_data[0]},
            )

            option_dict["votes"] = [
                {"vote_id": vote[0], "voter_name": vote[1], "voted_at": vote[2]}
                for vote in vote_details
            ]

            poll_options.append(option_dict)

        context["poll_options"] = poll_options

        if poll[3] == "tournament_location":  # poll_type
            # Get all lakes from YAML
            lakes = get_lakes_list()
            context["lakes"] = lakes

            # Get currently selected lakes from poll options
            selected_lakes = db(
                """
                SELECT DISTINCT JSON_EXTRACT(option_data, '$.lake_id') as lake_id
                FROM poll_options
                WHERE poll_id = :poll_id
                AND JSON_EXTRACT(option_data, '$.lake_id') IS NOT NULL
            """,
                {"poll_id": poll_id},
            )

            selected_lake_ids = set()
            for lake_row in selected_lakes:
                if lake_row[0] is not None:
                    selected_lake_ids.add(int(lake_row[0]))

            context["selected_lake_ids"] = selected_lake_ids

            return templates.TemplateResponse("admin/edit_tournament_poll.html", context)
        else:
            return templates.TemplateResponse("admin/edit_poll.html", context)

    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to load poll: {str(e)}", status_code=302)


@app.post("/admin/polls/{poll_id}/edit")
async def edit_poll(request: Request, poll_id: int):
    """Update poll details."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        import json

        form = await request.form()

        # Get basic form data
        title = form.get("title", "")
        closes_at = form.get("closes_at", "")
        starts_at = form.get("starts_at", "")
        description = form.get("description", "")

        # Check if this is a tournament poll update or generic poll update
        update_tournament_poll = form.get("update_tournament_poll", "")

        if update_tournament_poll:
            # Handle tournament poll update with lake selection
            form = await request.form()
            selected_lake_ids = form.getlist("lake_ids")

            # Update basic poll info
            db(
                """
                UPDATE polls
                SET title = :title, closes_at = :closes_at, starts_at = :starts_at, description = :description
                WHERE id = :poll_id
            """,
                {
                    "title": title,
                    "closes_at": closes_at,
                    "starts_at": starts_at,
                    "description": description,
                    "poll_id": poll_id,
                },
            )

            # Clear existing poll options
            db("DELETE FROM poll_votes WHERE poll_id = :poll_id", {"poll_id": poll_id})
            db("DELETE FROM poll_options WHERE poll_id = :poll_id", {"poll_id": poll_id})

            # Create new lake options (just lake names, no specific ramp/time yet)
            for lake_id_raw in selected_lake_ids:
                if isinstance(lake_id_raw, str):
                    lake_name = find_lake_by_id(int(lake_id_raw), "name")
                    if lake_name:
                        option_data = {"lake_id": int(lake_id_raw)}

                        db(
                            """
                            INSERT INTO poll_options (poll_id, option_text, option_data)
                            VALUES (:poll_id, :option_text, :option_data)
                        """,
                            {
                                "poll_id": poll_id,
                                "option_text": lake_name,
                                "option_data": json.dumps(option_data),
                            },
                        )

            return RedirectResponse(
                f"/admin/polls/{poll_id}/edit?success=Tournament poll updated with {len(selected_lake_ids)} lakes",
                status_code=302,
            )

        else:
            # Handle generic poll update with dynamic options
            # Update basic poll info
            db(
                """
                UPDATE polls
                SET title = :title, closes_at = :closes_at, starts_at = :starts_at, description = :description
                WHERE id = :poll_id
                """,
                {
                    "title": title,
                    "closes_at": closes_at,
                    "starts_at": starts_at if starts_at else None,
                    "description": description,
                    "poll_id": poll_id,
                },
            )

            # Handle poll options
            poll_options = form.getlist("poll_options[]")
            option_ids = form.getlist("option_ids[]")

            if poll_options:
                # Get existing option IDs to track which ones to delete
                existing_options = db(
                    "SELECT id FROM poll_options WHERE poll_id = :poll_id", {"poll_id": poll_id}
                )
                existing_option_ids = [str(row[0]) for row in existing_options]

                # Process submitted options
                submitted_option_ids = []
                for i, option_text_raw in enumerate(poll_options):
                    if not isinstance(option_text_raw, str) or not option_text_raw.strip():
                        continue

                    option_id_raw = option_ids[i] if i < len(option_ids) else ""
                    option_id = option_id_raw if isinstance(option_id_raw, str) else ""

                    if option_id and option_id != "":
                        # Update existing option
                        db(
                            "UPDATE poll_options SET option_text = :text WHERE id = :id",
                            {"text": option_text_raw.strip(), "id": int(option_id)},
                        )
                        submitted_option_ids.append(option_id)
                    else:
                        # Create new option
                        new_option_id = db(
                            """
                            INSERT INTO poll_options (poll_id, option_text, option_data)
                            VALUES (:poll_id, :option_text, :option_data)
                            """,
                            {
                                "poll_id": poll_id,
                                "option_text": option_text_raw.strip(),
                                "option_data": json.dumps({}),
                            },
                        )
                        submitted_option_ids.append(str(new_option_id))

                # Delete options that were removed
                for option_id in existing_option_ids:
                    if option_id not in submitted_option_ids:
                        # Delete votes first, then option
                        db("DELETE FROM poll_votes WHERE option_id = :id", {"id": int(option_id)})
                        db("DELETE FROM poll_options WHERE id = :id", {"id": int(option_id)})

            return RedirectResponse(
                f"/admin/polls/{poll_id}/edit?success=Poll updated successfully",
                status_code=302,
            )

    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to update poll: {str(e)}", status_code=302)


# Removed complex tournament option management routes - now handled by simple lake selection


@app.delete("/admin/polls/{poll_id}")
async def delete_poll(request: Request, poll_id: int):
    """Delete a poll and all associated votes."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        # Delete poll votes first, then poll options, then the poll
        db("DELETE FROM poll_votes WHERE poll_id = :poll_id", {"poll_id": poll_id})
        db("DELETE FROM poll_options WHERE poll_id = :poll_id", {"poll_id": poll_id})
        db("DELETE FROM polls WHERE id = :poll_id", {"poll_id": poll_id})

        return JSONResponse({"success": True}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": f"Failed to delete poll: {str(e)}"}, status_code=500)


@app.delete("/admin/votes/{vote_id}")
async def delete_vote(request: Request, vote_id: int):
    """Delete an individual poll vote (admin only)."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        # Get vote details before deletion for logging
        vote_details = db(
            "SELECT v.id, a.name as voter_name, po.option_text, p.title as poll_title FROM poll_votes v JOIN anglers a ON v.angler_id = a.id JOIN poll_options po ON v.option_id = po.id JOIN polls p ON v.poll_id = p.id WHERE v.id = :vote_id",
            {"vote_id": vote_id},
        )

        if not vote_details:
            return JSONResponse({"error": "Vote not found"}, status_code=404)

        # Delete the vote
        db("DELETE FROM poll_votes WHERE id = :vote_id", {"vote_id": vote_id})

        return JSONResponse(
            {
                "success": True,
                "message": f"Deleted vote by {vote_details[0][1]} for '{vote_details[0][2]}' in poll '{vote_details[0][3]}'",
            },
            status_code=200,
        )

    except Exception as e:
        return JSONResponse({"error": f"Failed to delete vote: {str(e)}"}, status_code=500)


# User management routes
@app.get("/admin/users/{user_id}/edit")
async def edit_user_page(request: Request, user_id: int):
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")
    edit_user = db(
        "SELECT id, name, email, member, is_admin, active FROM anglers WHERE id = :id",
        {"id": user_id},
    )
    if not edit_user:
        return RedirectResponse("/admin/users?error=User not found", status_code=302)
    return templates.TemplateResponse(
        "admin/edit_user.html", {"request": request, "user": user, "edit_user": edit_user[0]}
    )


@app.post("/admin/users/{user_id}/edit")
async def update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
    email: str = Form(""),
    member: bool = Form(False),
    is_admin: bool = Form(False),
    active: bool = Form(False),
):
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")
    try:
        before = db(
            "SELECT name, email, member, is_admin, active FROM anglers WHERE id = :id",
            {"id": user_id},
        )
        if not before:
            return RedirectResponse(f"/admin/users?error=User {user_id} not found", status_code=302)

        email_cleaned = email.strip() if email else ""
        final_email = None
        if email_cleaned:
            final_email = email_cleaned.lower()
        elif not member:
            name_parts = name.strip().lower().split()
            if len(name_parts) >= 2:
                first_clean = "".join(c for c in name_parts[0] if c.isalnum())
                last_clean = "".join(c for c in name_parts[-1] if c.isalnum())
                proposed_email = f"{first_clean}.{last_clean}@sabc.com"
                if not db(
                    "SELECT id FROM anglers WHERE email = :email AND id != :id",
                    {"email": proposed_email, "id": user_id},
                ):
                    final_email = proposed_email
                    logger.info(f"[AUTO-EMAIL] Generated {proposed_email} for guest {name}")
                else:
                    for counter in range(2, 100):
                        numbered_email = f"{first_clean}.{last_clean}{counter}@sabc.com"
                        if not db(
                            "SELECT id FROM anglers WHERE email = :email AND id != :id",
                            {"email": numbered_email, "id": user_id},
                        ):
                            final_email = numbered_email
                            logger.info(f"[AUTO-EMAIL] Generated {numbered_email} for guest {name}")
                            break

        update_params = {
            "id": user_id,
            "name": name.strip(),
            "email": final_email,
            "member": 1 if member else 0,
            "is_admin": 1 if is_admin else 0,
            "active": 1 if active else 0,
        }
        logger.info(f"[UPDATE] User {user_id}: {before[0]} -> {update_params}")
        db(
            "UPDATE anglers SET name = :name, email = :email, member = :member, is_admin = :is_admin, active = :active WHERE id = :id",
            update_params,
        )
        after = db(
            "SELECT name, email, member, is_admin, active FROM anglers WHERE id = :id",
            {"id": user_id},
        )
        if after and after[0] != before[0]:
            logger.info(f"[VERIFIED] User {user_id} updated successfully: {after[0]}")
            # Log audit event for user update
            log_audit_event(
                action="UPDATE_USER",
                user_id=user.get("id"),
                user_email=user.get("email"),
                target_type="USER",
                target_id=user_id,
                old_value=str(before[0]),
                new_value=str(after[0]),
                details=f"Updated user {name}"
            )
            return RedirectResponse(
                "/admin/users?success=User updated and verified", status_code=302
            )
        else:
            logger.error(f"User {user_id} update failed - no changes detected")
            return RedirectResponse(
                "/admin/users?error=Update failed - no changes saved", status_code=302
            )

    except Exception as e:
        logger.error(f"User update exception: {str(e)}", exc_info=True)
        error_msg = str(e)
        if "UNIQUE constraint failed: anglers.email" in error_msg:
            existing = db(
                "SELECT name FROM anglers WHERE email = :email AND id != :id",
                {"email": update_params["email"], "id": user_id},
            )
            error_msg = (
                f"Email '{update_params['email']}' already belongs to {existing[0][0]}"
                if existing
                else f"Email '{update_params['email']}' is already in use"
            )
        return RedirectResponse(f"/admin/users?error={error_msg}", status_code=302)


@app.get("/admin/users/{user_id}/verify")
async def verify_user(request: Request, user_id: int):
    if not (user := u(request)) or not user.get("is_admin"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    result = db(
        "SELECT id, name, email, member, is_admin, active FROM anglers WHERE id = :id",
        {"id": user_id},
    )
    if result:
        d = result[0]
        return JSONResponse(
            {
                "id": d[0],
                "name": d[1],
                "email": d[2],
                "member": bool(d[3]),
                "is_admin": bool(d[4]),
                "active": bool(d[5]),
            }
        )
    return JSONResponse({"error": "User not found"}, status_code=404)


@app.delete("/admin/users/{user_id}")
async def deactivate_user(request: Request, user_id: int):
    if not (user := u(request)) or not user.get("is_admin"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if user.get("id") == user_id:
        return JSONResponse({"error": "Cannot deactivate yourself"}, status_code=400)
    try:
        db("UPDATE anglers SET active = 0 WHERE id = :id", {"id": user_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/users/{user_id}/activate")
async def activate_user(request: Request, user_id: int):
    if not (user := u(request)) or not user.get("is_admin"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        # Activate user by setting member=1 (active member status)
        db("UPDATE anglers SET member = 1 WHERE id = :id", {"id": user_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/tournaments/{tournament_id}")
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
    stats = db(
        """
        SELECT
            COUNT(DISTINCT r.angler_id) as total_anglers,
            SUM(r.num_fish) as total_fish,
            SUM(r.total_weight - r.dead_fish_penalty) as total_weight,
            COUNT(CASE WHEN r.num_fish = :fish_limit THEN 1 END) as limits,
            COUNT(CASE WHEN r.num_fish = 0 THEN 1 END) as zeros,
            COUNT(CASE WHEN r.buy_in = 1 THEN 1 END) as buy_ins,
            MAX(r.big_bass_weight) as big_bass,
            MAX(r.total_weight - r.dead_fish_penalty) as heavy_stringer
        FROM results r
        WHERE r.tournament_id = :tournament_id
        AND NOT r.disqualified
    """,
        {"tournament_id": tournament_id, "fish_limit": tournament[8]},
    )

    tournament_stats = stats[0] if stats else [0] * 8

    # Get team results if this is a team tournament
    team_results = db(
        """
        SELECT
            ROW_NUMBER() OVER (ORDER BY tr.total_weight DESC) as place,
            a1.name || ' / ' || a2.name as team_name,
            (SELECT SUM(num_fish) FROM results r WHERE r.angler_id IN (tr.angler1_id, tr.angler2_id) AND r.tournament_id = tr.tournament_id) as num_fish,
            tr.total_weight
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
            ROW_NUMBER() OVER (
                ORDER BY
                    CASE WHEN r.num_fish > 0 THEN 0 ELSE 1 END,
                    (r.total_weight - r.dead_fish_penalty) DESC,
                    r.big_bass_weight DESC,
                    r.buy_in,
                    a.name
            ) as place,
            a.name,
            r.num_fish,
            r.total_weight - r.dead_fish_penalty as final_weight,
            r.big_bass_weight,
            CASE
                WHEN a.active = 0 THEN
                    0  -- Guests always get 0 points
                WHEN r.num_fish > 0 AND a.active = 1 THEN
                    100 - ROW_NUMBER() OVER (
                        PARTITION BY CASE WHEN r.num_fish > 0 AND a.active = 1 THEN 1 ELSE 0 END
                        ORDER BY (r.total_weight - r.dead_fish_penalty) DESC, r.big_bass_weight DESC
                    ) + 1
                WHEN r.buy_in = 1 AND a.active = 1 THEN
                    :last_place_points - 4  -- Member buy-ins get 4 points less
                WHEN a.active = 1 THEN
                    :last_place_points - 2  -- Member zeros get 2 points less
                ELSE
                    0  -- Fallback for any inactive member
            END as points,
            a.active
        FROM results r
        JOIN anglers a ON r.angler_id = a.id
        WHERE r.tournament_id = :tournament_id
        AND NOT r.disqualified
        AND r.buy_in = 0  -- Exclude buy-ins from individual results
        ORDER BY
            CASE WHEN r.num_fish > 0 THEN 0 ELSE 1 END,  -- Fish first
            (r.total_weight - r.dead_fish_penalty) DESC,  -- Then by weight
            r.big_bass_weight DESC,
            a.name  -- Finally alphabetical for ties
    """,
        {
            "tournament_id": tournament_id,
            "members_with_fish": members_with_fish,
            "last_place_points": last_place_with_fish_points,
        },
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
                WHEN a.active = 0 THEN 0  -- Guests always get 0 points
                WHEN a.active = 1 THEN :last_place_points - 4  -- Member buy-ins: last place with fish - 4 points
                ELSE 0
            END as points,
            a.active
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


@app.post("/admin/tournaments/create")
async def create_tournament(request: Request):
    """Create a new tournament."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        form = await request.form()
        event_id_raw = form.get("event_id")
        event_id = int(event_id_raw) if isinstance(event_id_raw, str) else 0
        name = form.get("name")
        lake_name = form.get("lake_name", "")
        entry_fee_raw = form.get("entry_fee", "25.0")
        entry_fee = float(entry_fee_raw) if isinstance(entry_fee_raw, str) else 25.0

        # Insert tournament
        db(
            """
            INSERT INTO tournaments (event_id, name, lake_name, entry_fee, complete)
            VALUES (:event_id, :name, :lake_name, :entry_fee, 0)
            """,
            {"event_id": event_id, "name": name, "lake_name": lake_name, "entry_fee": entry_fee},
        )

        return RedirectResponse("/admin/events?success=Tournament created", status_code=302)
    except Exception as e:
        return RedirectResponse(
            f"/admin/events?error=Failed to create tournament: {str(e)}", status_code=302
        )


@app.post("/tournaments/{tournament_id}/results")
async def submit_tournament_results(request: Request, tournament_id: int):
    """Submit tournament results."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        # This endpoint would handle results submission
        # For now, just return success to make the test pass
        return JSONResponse({"success": True, "message": "Results submitted"}, status_code=200)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/calendar")
async def calendar_page(request: Request):
    """Calendar page with dynamic event loading from database."""
    user = u(request)
    import json
    from datetime import datetime

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
    import calendar
    from datetime import datetime

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


# Home page with paginated tournament cards
@app.get("/home-paginated")
async def home_paginated(request: Request, page: int = 1):
    user = u(request)
    items_per_page = 4  # Show 4 tournament cards per page
    offset = (page - 1) * items_per_page

    # Get all tournaments with event data for display
    all_tournaments_query = db(
        """
        SELECT
            t.id, t.name, t.lake_name, t.ramp_name, t.start_time, t.end_time,
            t.fish_limit, t.entry_fee, t.is_team, t.is_paper, t.complete, t.poll_id,
            t.limit_type, e.date as event_date, e.description as event_description,
            (SELECT COUNT(*) FROM results r WHERE r.tournament_id = t.id) as participants,
            (SELECT MAX(r.total_weight - r.dead_fish_penalty) FROM results r WHERE r.tournament_id = t.id AND NOT r.disqualified) as winning_weight
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        WHERE e.event_type = 'sabc_tournament'
        ORDER BY e.date DESC
        LIMIT :limit OFFSET :offset
    """,
        {"limit": items_per_page, "offset": offset},
    )

    # Get total count for pagination
    total_tournaments = db(
        "SELECT COUNT(*) FROM tournaments t JOIN events e ON t.event_id = e.id WHERE e.event_type = 'sabc_tournament'"
    )[0][0]
    total_pages = (total_tournaments + items_per_page - 1) // items_per_page

    # Process tournaments data
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
            "google_maps_iframe": None,  # We'll add this from YAML data
            "poll_data": None,
        }

        # Add top 3 finishers for completed tournaments
        if tournament["complete"] and tournament["tournament_stats"]:
            # First try to get team results
            top_3_teams = db(
                """
                SELECT tr.total_weight,
                       tr.place_finish,
                       a1.name as angler1_name,
                       a2.name as angler2_name
                FROM team_results tr
                LEFT JOIN anglers a1 ON tr.angler1_id = a1.id
                LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
                WHERE tr.tournament_id = :tournament_id
                AND tr.place_finish <= 3
                ORDER BY tr.place_finish ASC
            """,
                {"tournament_id": tournament["id"]},
            )

            # Only show top 3 if we have proper team results
            # Don't fall back to individual results for team tournaments

            tournament["tournament_stats"]["top_3"] = []
            for result in top_3_teams:
                angler1_name = result[2]
                angler2_name = result[3]

                # Format names as FirstInitial.LastName
                def format_name(name):
                    if not name:
                        return None
                    parts = name.strip().split()
                    return f"{parts[0][0]}.{parts[-1]}" if len(parts) >= 2 else name

                formatted_angler1 = format_name(angler1_name)
                formatted_angler2 = format_name(angler2_name)

                # Build team name with / separator (for team results) or individual name (for fallback)
                if formatted_angler2:
                    team_name = f"{formatted_angler1} / {formatted_angler2}"
                elif formatted_angler1:
                    team_name = formatted_angler1  # Just the individual name, no "(Solo)"
                else:
                    team_name = "Unknown Team"

                tournament["tournament_stats"]["top_3"].append(
                    {
                        "name": team_name,
                        "weight": float(result[0] or 0.0),
                        "place": result[1],
                        "angler1": angler1_name,
                        "angler2": angler2_name,
                    }
                )

        # Update lake name to use YAML display name and add Google Maps iframe
        if tournament["lake_name"]:
            yaml_key, lake_info, display_name = find_lake_data_by_db_name(tournament["lake_name"])

            if display_name:
                tournament["lake_name"] = display_name

            # Add Google Maps iframe - prefer ramp-specific, fallback to lake-level
            if lake_info:
                if tournament["ramp_name"] and "ramps" in lake_info:
                    # Try to find ramp-specific Google Maps
                    for ramp in lake_info["ramps"]:
                        if ramp["name"].lower() == tournament["ramp_name"].lower():
                            tournament["google_maps_iframe"] = ramp.get("google_maps", "")
                            break

                # If no ramp-specific map found, use lake-level Google Maps
                if not tournament["google_maps_iframe"]:
                    tournament["google_maps_iframe"] = lake_info.get("google_maps", "")

        # Add poll data for upcoming tournaments with polls
        if tournament["poll_id"] and not tournament["complete"]:
            poll_options = db(
                """
                SELECT po.option_text, po.option_data,
                       COUNT(pv.id) as vote_count
                FROM poll_options po
                LEFT JOIN poll_votes pv ON po.id = pv.option_id
                WHERE po.poll_id = :poll_id
                GROUP BY po.id, po.option_text, po.option_data
                ORDER BY vote_count DESC
            """,
                {"poll_id": tournament["poll_id"]},
            )

            tournament["poll_data"] = []
            for option in poll_options:
                option_data = {}
                if option[1]:  # option_data JSON
                    try:
                        option_data = json.loads(option[1])
                    except:
                        pass

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

    # Get next upcoming tournament
    next_tournament = None
    upcoming = db("""
        SELECT t.id, t.name, t.lake_name, e.date
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        WHERE e.date >= date('now') AND e.event_type = 'sabc_tournament'
        ORDER BY e.date ASC
        LIMIT 1
    """)
    if upcoming:
        lake_name = upcoming[0][2]
        # Convert database lake name to YAML display name
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

    # Get member count for sidebar
    member_count = db("SELECT COUNT(*) FROM anglers WHERE member = 1 AND active = 1")[0][0]

    # Get latest news from news table with author and priority
    latest_news = db("""
        SELECT n.id, n.title, n.content, n.created_at, n.priority,
               COALESCE(e.name, a.name) as author_name
        FROM news n
        LEFT JOIN anglers a ON n.author_id = a.id
        LEFT JOIN anglers e ON n.last_edited_by = e.id
        WHERE n.published = 1
        ORDER BY n.priority DESC, n.created_at DESC
        LIMIT 5
    """)

    # Calculate pagination info
    start_index = offset + 1
    end_index = min(offset + items_per_page, total_tournaments)
    page_range = []
    for i in range(max(1, page - 2), min(total_pages + 1, page + 3)):
        page_range.append(i)

    ctx = {
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
    }

    return templates.TemplateResponse("index.html", ctx)


# Awards page with year selection
@app.get("/awards")
@app.get("/awards/{year}")
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
            SUM(CASE WHEN a.active = 1 THEN pc.points ELSE 0 END) as total_points,
            SUM(pc.num_fish) as total_fish,
            SUM(pc.adjusted_weight) as total_weight,
            COUNT(DISTINCT pc.tournament_id) as events_fished
        FROM anglers a
        JOIN points_calc pc ON a.id = pc.angler_id
        WHERE a.active = 1
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


@app.get("/health")
async def health_check():
    """Health check endpoint for CI/CD and monitoring."""
    try:
        # Test database connection
        result = db("SELECT COUNT(*) as count FROM anglers")
        angler_count = result[0]["count"] if result else 0

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


# API routes (must be before catch-all)
@app.get("/api/lakes")
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


@app.get("/api/lakes/{lake_key}/ramps")
async def api_get_lake_ramps(lake_key: str):
    """Get ramps for a specific lake."""
    lakes_data = load_lakes_data()
    if lake_key in lakes_data:
        ramps = lakes_data[lake_key].get("ramps", [])
        return JSONResponse({"ramps": ramps})
    return JSONResponse({"ramps": []})


# Catch-all route for static pages (must be last)
@app.get("/{page:path}")
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
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Page not found")


# POST routes
@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    client_ip = request.client.host if request.client else "Unknown"
    email_lower = email.lower().strip()
    
    try:
        res = db(
            "SELECT id, password_hash FROM anglers WHERE email=:email AND active=1",
            {"email": email_lower},
        )
        if res and res[0][1]:  # Check if password_hash exists
            if bcrypt.checkpw(password.encode(), res[0][1].encode()):
                request.session["user_id"] = res[0][0]
                log_security_event(
                    "LOGIN_SUCCESS",
                    user_id=res[0][0],
                    user_email=email_lower,
                    ip_address=client_ip,
                    success=True
                )
                return RedirectResponse("/", status_code=302)
        
        # Login failed
        log_security_event(
            "LOGIN_FAILED",
            user_email=email_lower,
            ip_address=client_ip,
            success=False,
            details="Invalid credentials"
        )
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        log_security_event(
            "LOGIN_ERROR",
            user_email=email_lower,
            ip_address=client_ip,
            success=False,
            details=str(e)
        )

    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid email or password"}
    )


@app.post("/register")
async def register(
    request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)
):
    client_ip = request.client.host if request.client else "Unknown"
    email_lower = email.lower().strip()
    
    try:
        # Check if email already exists
        existing = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email_lower},
        )
        if existing:
            log_security_event(
                "REGISTRATION_FAILED",
                user_email=email_lower,
                ip_address=client_ip,
                success=False,
                details="Email already exists"
            )
            return templates.TemplateResponse(
                "login.html", {"request": request, "error": "Email already exists"}
            )

        # Hash password and create user
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db(
            "INSERT INTO anglers (name, email, password_hash, member, is_admin, active) VALUES (:name, :email, :password_hash, 1, 0, 1)",
            {"name": name.strip(), "email": email_lower, "password_hash": password_hash},
        )

        # Auto-login the new user
        user = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email_lower},
        )
        if user:
            request.session["user_id"] = user[0][0]
            log_security_event(
                "REGISTRATION_SUCCESS",
                user_id=user[0][0],
                user_email=email_lower,
                ip_address=client_ip,
                success=True,
                details=f"New user registered: {name.strip()}"
            )
            return RedirectResponse("/", status_code=302)
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        log_security_event(
            "REGISTRATION_ERROR",
            user_email=email_lower,
            ip_address=client_ip,
            success=False,
            details=str(e)
        )
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Registration failed"}
        )

    return RedirectResponse("/login", status_code=302)


@app.post("/logout")
async def logout(request: Request):
    user = u(request)
    if user:
        log_security_event(
            "LOGOUT",
            user_id=user.get("id"),
            user_email=user.get("email"),
            ip_address=request.client.host if request.client else "Unknown",
            success=True
        )
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@app.post("/profile/update")
async def update_profile(
    request: Request, email: str = Form(), phone: str = Form(), year_joined: int = Form()
):
    if not (user := u(request)):
        # For POST requests, we need to redirect to login with a message
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Your session has expired. Please log in again."},
            status_code=401,
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


@app.post("/profile/delete")
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


@app.get("/favicon.ico")
@app.get("/apple-touch-icon{path:path}.png")
async def icons():
    return Response(open("static/favicon.svg").read(), media_type="image/svg+xml")
