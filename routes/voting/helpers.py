import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy import exists, false, func, select

from core.db_schema import Event, Poll, PollOption, PollVote, Tournament, engine, get_session
from core.helpers.timezone import now_local
from core.query_service import QueryService


def get_poll_options(poll_id: int, is_admin: bool = False) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_poll_options_with_votes(poll_id, include_details=is_admin)


def process_closed_polls() -> int:
    try:
        with get_session() as session:
            # Find closed polls that need processing
            now = now_local()
            closed_polls_query = (
                select(Poll.id, Poll.event_id, Poll.poll_type, Poll.closes_at)
                .join(Event, Poll.event_id == Event.id)
                .where(Poll.closed.is_(false()))
                .where(Poll.closes_at < now)
                .where(Poll.poll_type == "tournament_location")
                .where(
                    ~exists(
                        select(1)
                        .where(Tournament.event_id == Poll.event_id)
                        .correlate_except(Tournament)
                    )
                )
                .where(Event.event_type == "sabc_tournament")
            )

            closed_polls = session.execute(closed_polls_query).all()

            for poll_id, event_id, poll_type, closes_at in closed_polls:
                # Mark poll as closed
                poll = session.query(Poll).filter(Poll.id == poll_id).first()
                if poll:
                    poll.closed = True

                # Find winning option (most votes, ties broken by lowest ID)
                vote_counts_subquery = (
                    select(PollOption.id, func.count(PollVote.id).label("vote_count"))
                    .outerjoin(PollVote, PollVote.option_id == PollOption.id)
                    .where(PollOption.poll_id == poll_id)
                    .group_by(PollOption.id)
                    .subquery()
                )

                max_votes = session.query(func.max(vote_counts_subquery.c.vote_count)).scalar() or 0

                winning_option_query = (
                    select(PollOption.id, PollOption.option_text, PollOption.option_data)
                    .join(vote_counts_subquery, PollOption.id == vote_counts_subquery.c.id)
                    .where(vote_counts_subquery.c.vote_count == max_votes)
                    .order_by(PollOption.id)
                    .limit(1)
                )

                winning_option_result = session.execute(winning_option_query).first()

                if not winning_option_result:
                    continue

                option_id, option_text, option_data_str = winning_option_result

                # Update poll with winning option
                if poll:
                    poll.winning_option_id = option_id

                # Create tournament from winning option
                if poll_type == "tournament_location":
                    try:
                        option_data = json.loads(option_data_str) if option_data_str else {}

                        # Get event details
                        event = session.query(Event).filter(Event.id == event_id).first()
                        if not event:
                            continue

                        lake_id = option_data.get("lake_id")
                        ramp_id = option_data.get("ramp_id")
                        tournament_start_time = option_data.get(
                            "start_time", str(event.start_time) if event.start_time else "06:00"
                        )
                        tournament_end_time = option_data.get(
                            "end_time", str(event.weigh_in_time) if event.weigh_in_time else "15:00"
                        )

                        # Parse lake and ramp names from option text
                        lake_name, ramp_name = "", ""
                        if option_text and " - " in option_text:
                            parts = option_text.split(" - ")
                            lake_name = parts[0].strip()
                            ramp_name = parts[1].split(" (")[0].strip()

                        # Convert time strings to time objects
                        start_time_obj = (
                            datetime.strptime(tournament_start_time, "%H:%M").time()
                            if isinstance(tournament_start_time, str)
                            else tournament_start_time
                        )
                        end_time_obj = (
                            datetime.strptime(tournament_end_time, "%H:%M").time()
                            if isinstance(tournament_end_time, str)
                            else tournament_end_time
                        )

                        # Create tournament
                        new_tournament = Tournament(
                            event_id=event_id,
                            poll_id=poll_id,
                            name=event.name,
                            lake_id=lake_id,
                            ramp_id=ramp_id,
                            lake_name=lake_name,
                            ramp_name=ramp_name,
                            entry_fee=event.entry_fee or Decimal("25.0"),
                            fish_limit=5,  # Default fish limit
                            start_time=start_time_obj,
                            end_time=end_time_obj,
                            complete=False,
                            is_team=True,
                            is_paper=False,
                        )
                        session.add(new_tournament)

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

            return len(closed_polls)
    except Exception:
        return 0
