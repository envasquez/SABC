"""Query strings for event service."""


def get_upcoming_admin_query() -> str:
    """Get SQL query for upcoming events in admin interface."""
    return """
        SELECT e.id, e.date, e.name, e.description, e.event_type,
               EXTRACT(DOW FROM e.date) as day_num,
               CASE EXTRACT(DOW FROM e.date)
                   WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
                   WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
                   WHEN 6 THEN 'Saturday'
               END as day_name,
               EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
               EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
               EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id
                   AND CURRENT_TIMESTAMP BETWEEN p.starts_at AND p.closes_at) as poll_active,
               e.start_time, e.weigh_in_time, e.entry_fee, e.lake_name,
               e.ramp_name, e.holiday_name,
               EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id
                   AND t.complete = true) as tournament_complete
        FROM events e
        WHERE e.date >= CURRENT_DATE
        ORDER BY e.date
        LIMIT :limit OFFSET :offset
    """


def get_past_admin_query() -> str:
    """Get SQL query for past events in admin interface."""
    return """
        SELECT e.id, e.date, e.name, e.description, e.event_type, e.entry_fee,
               e.lake_name, e.start_time, e.weigh_in_time, e.holiday_name,
               EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
               EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
               EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id
                   AND t.complete = true) as tournament_complete,
               EXISTS(SELECT 1 FROM tournaments t JOIN results r ON t.id = r.tournament_id
                   WHERE t.event_id = e.id) as has_results
        FROM events e
        WHERE e.date < CURRENT_DATE AND event_type != 'holiday'
        ORDER BY e.date DESC
        LIMIT :limit OFFSET :offset
    """
