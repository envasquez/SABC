import json

from core.db_schema import engine
from core.query_service import QueryService
from routes.dependencies import db


def get_poll_options(poll_id: int, is_admin: bool = False):
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_poll_options_with_votes(poll_id, include_details=is_admin)


def process_closed_polls() -> int:
    try:
        closed_polls = db(
            """SELECT p.id, p.event_id, p.poll_type, p.closes_at FROM polls p
            JOIN events e ON p.event_id = e.id
            WHERE p.closed = FALSE AND CURRENT_TIMESTAMP > p.closes_at
            AND p.poll_type = 'tournament_location'
            AND NOT EXISTS (SELECT 1 FROM tournaments t WHERE t.event_id = p.event_id)
            AND e.event_type = 'sabc_tournament'"""
        )
        for poll_id, event_id, poll_type, closes_at in closed_polls:
            db("UPDATE polls SET closed = TRUE WHERE id = :poll_id", {"poll_id": poll_id})
            winning_option = db(
                """SELECT po.id, po.option_text, po.option_data FROM poll_options po
                WHERE po.poll_id = :poll_id
                AND (SELECT COUNT(*) FROM poll_votes pv WHERE pv.option_id = po.id) = (
                    SELECT MAX(vote_count) FROM (
                        SELECT COUNT(*) as vote_count FROM poll_votes pv2
                        JOIN poll_options po2 ON pv2.option_id = po2.id
                        WHERE po2.poll_id = :poll_id GROUP BY po2.id
                    ) AS subq
                ) ORDER BY po.id LIMIT 1""",
                {"poll_id": poll_id},
            )
            if not winning_option:
                continue
            option_id, option_text, option_data_str = winning_option[0]
            db(
                "UPDATE polls SET winning_option_id = :option_id WHERE id = :poll_id",
                {"option_id": option_id, "poll_id": poll_id},
            )
            if poll_type == "tournament_location":
                try:
                    option_data = json.loads(option_data_str) if option_data_str else {}
                    event_details = db(
                        """SELECT e.name, e.date, e.entry_fee, e.fish_limit, e.start_time, e.weigh_in_time
                        FROM events e WHERE e.id = :event_id""",
                        {"event_id": event_id},
                    )
                    if not event_details:
                        continue
                    event_name, event_date, entry_fee, fish_limit, start_time, weigh_in_time = (
                        event_details[0]
                    )
                    lake_id, ramp_id = option_data.get("lake_id"), option_data.get("ramp_id")
                    tournament_start_time = option_data.get("start_time", start_time or "06:00")
                    tournament_end_time = option_data.get("end_time", weigh_in_time or "15:00")
                    lake_name, ramp_name = "", ""
                    if option_text and " - " in option_text:
                        parts = option_text.split(" - ")
                        lake_name, ramp_name = parts[0].strip(), parts[1].split(" (")[0].strip()
                    db(
                        """INSERT INTO tournaments (event_id, poll_id, name, lake_id, ramp_id, lake_name, ramp_name,
                        entry_fee, fish_limit, start_time, end_time, complete, is_team, is_paper)
                        VALUES (:event_id, :poll_id, :name, :lake_id, :ramp_id, :lake_name, :ramp_name,
                        :entry_fee, :fish_limit, :start_time, :end_time, FALSE, TRUE, FALSE)""",
                        {
                            "event_id": event_id,
                            "poll_id": poll_id,
                            "name": event_name,
                            "lake_id": lake_id,
                            "ramp_id": ramp_id,
                            "lake_name": lake_name,
                            "ramp_name": ramp_name,
                            "entry_fee": entry_fee or 25.0,
                            "fish_limit": fish_limit or 5,
                            "start_time": tournament_start_time,
                            "end_time": tournament_end_time,
                        },
                    )
                except (json.JSONDecodeError, KeyError):
                    continue
        return len(closed_polls)
    except Exception:
        return 0
