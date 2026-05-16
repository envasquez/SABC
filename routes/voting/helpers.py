import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import case, distinct, exists, extract, false, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.db_schema import (
    Event,
    Lake,
    Poll,
    PollOption,
    PollVote,
    Ramp,
    Result,
    Tournament,
    engine,
    get_session,
)
from core.helpers.logging import get_logger
from core.helpers.timezone import now_local
from core.query_service import QueryService

logger = get_logger(__name__)


def get_poll_options(
    poll_id: int,
    is_admin: bool = False,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Fetch poll options with vote counts.

    If ``session`` is provided we re-use its bind connection rather than
    opening a fresh ``engine.connect()`` per call. This is critical when
    called inside a loop (see ``list_polls.py``) — opening a new connection
    each iteration was previously the single largest source of connection
    churn on the /polls page.
    """
    if session is not None:
        bind = session.connection()
        qs = QueryService(bind)
        return qs.get_poll_options_with_votes(poll_id, include_details=is_admin)

    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_poll_options_with_votes(poll_id, include_details=is_admin)


def get_seasonal_tournament_history(
    session: Session, poll: Poll, years_back: int = 4
) -> List[Dict[str, Any]]:
    """
    Get tournament history for the same month as the poll's event date.

    For a November 2025 poll, returns data for November tournaments
    from previous years (2024, 2023, 2022, 2021).

    Uses a single windowed query to fetch all ``years_back`` years at
    once (previously fired 3 queries × years_back per poll = an N+1 of
    12+ round trips on the /polls page).

    Args:
        session: Database session
        poll: The poll object
        years_back: Number of years to look back (default: 4)

    Returns:
        List of tournament history dictionaries with stats
    """
    # Get the poll's associated event to determine month
    if not poll.event_id:
        return []

    event = session.query(Event).filter(Event.id == poll.event_id).first()
    if not event:
        return []

    target_month = event.date.month  # e.g., 11 for November
    target_year = event.date.year
    month_name = event.date.strftime("%B")  # "November"

    # Build the year range we care about: [target_year - years_back, ..., target_year - 1].
    past_years = [target_year - i for i in range(1, years_back + 1)]
    if not past_years:
        return []

    # 1) One query: tournament-level rollup for each (month=target_month, year in past_years).
    #    Aggregates num_anglers, num_zeros, num_limits (filtered count). The fish_limit
    #    threshold is applied as a CASE WHEN so we don't need a second pass.
    fish_limit_threshold = func.coalesce(Tournament.fish_limit, 5)
    tournament_rows = (
        session.query(
            Tournament.id.label("tournament_id"),
            Tournament.fish_limit,
            Tournament.start_time,
            Tournament.end_time,
            Event.date,
            extract("year", Event.date).label("event_year"),
            Lake.display_name.label("lake_name"),
            Ramp.name.label("ramp_name"),
            func.count(distinct(Result.angler_id)).label("num_anglers"),
            func.sum(case((Result.total_weight == 0, 1), else_=0)).label("num_zeros"),
            func.sum(
                case(
                    (
                        (Result.num_fish >= fish_limit_threshold)
                        & (Result.disqualified.is_(False)),
                        1,
                    ),
                    else_=0,
                )
            ).label("num_limits"),
        )
        .join(Event, Tournament.event_id == Event.id)
        .outerjoin(Lake, Tournament.lake_id == Lake.id)
        .outerjoin(Ramp, Tournament.ramp_id == Ramp.id)
        .outerjoin(Result, Tournament.id == Result.tournament_id)
        .filter(
            Tournament.complete.is_(True),
            extract("month", Event.date) == target_month,
            extract("year", Event.date).in_(past_years),
        )
        .group_by(
            Tournament.id,
            Tournament.fish_limit,
            Tournament.start_time,
            Tournament.end_time,
            Event.date,
            Lake.display_name,
            Ramp.name,
        )
        .order_by(Event.date.desc())
        .all()
    )

    if not tournament_rows:
        return []

    # Pick one tournament per year (matches previous .first() with order_by date desc).
    tournament_by_year: Dict[int, Any] = {}
    for row in tournament_rows:
        yr = int(row.event_year)
        if yr not in tournament_by_year:
            tournament_by_year[yr] = row

    tournament_ids = [row.tournament_id for row in tournament_by_year.values()]

    # 2) One query: top-3 weights per tournament using ROW_NUMBER(). Group client-side.
    top_weights_by_tid: Dict[int, List[float]] = {tid: [] for tid in tournament_ids}
    if tournament_ids:
        row_num = (
            func.row_number()
            .over(
                partition_by=Result.tournament_id,
                order_by=Result.total_weight.desc(),
            )
            .label("rn")
        )
        ranked_subq = (
            session.query(
                Result.tournament_id.label("tournament_id"),
                Result.total_weight.label("total_weight"),
                row_num,
            )
            .filter(
                Result.tournament_id.in_(tournament_ids),
                Result.disqualified.is_(False),
            )
            .subquery()
        )
        top_rows = (
            session.query(
                ranked_subq.c.tournament_id,
                ranked_subq.c.total_weight,
            )
            .filter(ranked_subq.c.rn <= 3)
            .order_by(ranked_subq.c.tournament_id.asc(), ranked_subq.c.rn.asc())
            .all()
        )
        for tid, weight in top_rows:
            top_weights_by_tid[tid].append(float(weight))

    # Assemble the history list in the same order/shape as before
    # (most recent past year first).
    history: List[Dict[str, Any]] = []
    for past_year in past_years:
        row = tournament_by_year.get(past_year)
        if not row:
            continue
        history.append(
            {
                "tournament_id": row.tournament_id,
                "year": past_year,
                "month_name": month_name,
                "date": row.date,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "lake_name": row.lake_name or "TBD",
                "ramp_name": row.ramp_name or "TBD",
                "num_anglers": row.num_anglers or 0,
                "num_limits": int(row.num_limits or 0),
                "num_zeros": row.num_zeros or 0,
                "top_3_weights": top_weights_by_tid.get(row.tournament_id, []),
            }
        )

    return history


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
                            entry_fee=event.entry_fee or Decimal("50.0"),
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
    except SQLAlchemyError:
        # process_closed_polls is the only path that materializes tournaments
        # from won polls — silently swallowing errors would hide real bugs.
        # Log with full traceback and re-raise so callers (e.g. background
        # schedulers) see the failure.
        logger.exception("process_closed_polls failed")
        raise
