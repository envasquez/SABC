"""Season leaderboards on the 2026+ team-format awards page.

Builds a three-tournament 2026 season whose every metric is hand-computed in
the module docstring below, then asserts the page's boards against it. The
money math is the part worth pinning down: payouts are derived, not stored,
and the big bass pot rolls between tournaments.

Season layout (3 boats per event, so place money is $60 / $42 / $24 and the
big bass pot contributes $24 per event):

    T1  2026-03-14   Alice & Bob   20.00 lbs  5 fish  bb 5.50  1st
                     Carl & Dana   15.00 lbs  4 fish  bb 3.00  2nd
                     Erin & Frank  10.00 lbs  3 fish  bb 2.00  3rd
        Alice & Bob clear 5 lbs, so they take $60 + the $24 pot = $84.

    T2  2026-04-11   Alice & Carl  18.00 lbs  5 fish  bb 4.00  1st
                     Bob & Dana    12.00 lbs  4 fish  bb 3.50  2nd
                     Erin & Frank   8.00 lbs  2 fish  bb 1.00  3rd
        No qualifying bass -- the $24 pot rolls forward.

    T3  2026-05-09   Alice & Dana  22.00 lbs  5 fish  bb 6.00  1st
                     Bob & Carl    14.00 lbs  4 fish  bb 2.00  2nd
                     Erin & Frank   9.00 lbs  3 fish  bb 1.50  3rd
        Alice & Dana take $60 + the $24 pot + $24 rolled over = $108.

Totals: $450 paid out over the season; per angler (50/50 per boat) Alice
$126, Dana $96, Bob $84, Carl $72, Erin $36, Frank $36.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Tuple, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, TeamResult, Tournament, engine
from core.query_service import QueryService
from routes.pages.awards_boards import build_boards
from routes.pages.awards_helpers import (
    get_angler_season_stats_query,
    get_team_big_bass_query,
    get_team_heavy_stringer_query,
    get_team_season_stats_query,
)
from routes.pages.awards_money import (
    PLACE_PAYOUTS_PER_BOAT,
    _award_place_money,
    calculate_season_earnings,
)

#: ``(date, [(angler1, angler2, weight, fish, big bass, place)])`` per event.
SEASON: Tuple[Tuple[date, List[Tuple[str, str, str, int, str, int]]], ...] = (
    (
        date(2026, 3, 14),
        [
            ("Alice", "Bob", "20.00", 5, "5.50", 1),
            ("Carl", "Dana", "15.00", 4, "3.00", 2),
            ("Erin", "Frank", "10.00", 3, "2.00", 3),
        ],
    ),
    (
        date(2026, 4, 11),
        [
            ("Alice", "Carl", "18.00", 5, "4.00", 1),
            ("Bob", "Dana", "12.00", 4, "3.50", 2),
            ("Erin", "Frank", "8.00", 2, "1.00", 3),
        ],
    ),
    (
        date(2026, 5, 9),
        [
            ("Alice", "Dana", "22.00", 5, "6.00", 1),
            ("Bob", "Carl", "14.00", 4, "2.00", 2),
            ("Erin", "Frank", "9.00", 3, "1.50", 3),
        ],
    ),
)

ANGLER_NAMES = ("Alice", "Bob", "Carl", "Dana", "Erin", "Frank")


@pytest.fixture
def season_2026(db_session: Session) -> Dict[str, Angler]:
    """Materialize the season described in the module docstring."""
    anglers = {
        name: Angler(name=f"{name} Angler", email=f"{name.lower()}@example.com", member=True)
        for name in ANGLER_NAMES
    }
    db_session.add_all(anglers.values())
    db_session.commit()

    for index, (event_date, boats) in enumerate(SEASON, start=1):
        event = Event(
            date=event_date,
            year=2026,
            name=f"2026 Event {index}",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.commit()
        tournament = Tournament(
            event_id=event.id,
            name=event.name,
            fish_limit=5,
            entry_fee=Decimal("50.00"),
            is_team=True,
            complete=True,
            aoy_points=False,  # team format
            limit_type="boat",
        )
        db_session.add(tournament)
        db_session.commit()
        for a1, a2, weight, fish, big_bass, place in boats:
            db_session.add(
                TeamResult(
                    tournament_id=tournament.id,
                    angler1_id=anglers[a1].id,
                    angler2_id=anglers[a2].id,
                    num_fish=fish,
                    total_weight=Decimal(weight),
                    big_bass_weight=Decimal(big_bass),
                    place_finish=place,
                )
            )
        db_session.commit()
    return anglers


@pytest.fixture
def season_2025_event(db_session: Session) -> Event:
    """A pre-2026 event, so /awards/2025 is a selectable year.

    The route snaps an unknown year to the most recent one it has events
    for, so without this the 2025 request would silently render 2026.
    """
    event = Event(
        date=date(2025, 5, 10),
        year=2025,
        name="2025 Event",
        event_type="sabc_tournament",
    )
    db_session.add(event)
    db_session.commit()
    return event


def _boards(grain: str) -> Dict[str, object]:
    """Run the real query + board pipeline for one grain against the test DB."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        angler_earnings, team_earnings, total_paid = calculate_season_earnings(qs, 2026)
        if grain == "angler":
            rows = qs.fetch_all(get_angler_season_stats_query(), {"year": 2026})
            built = build_boards(rows, angler_earnings, "angler_id")
        else:
            rows = qs.fetch_all(get_team_season_stats_query(), {"year": 2026})
            built = build_boards(rows, team_earnings, "team_key")
    return {**built, "total_paid": total_paid}


class TestAnglerSeasonBoards:
    """Per-angler boards credit each angler with the boat they fished."""

    def test_place_counts_per_angler(self, season_2026):
        standings = {row["name"]: row for row in _boards("angler")["standings"]}
        assert len(standings) == 6

        alice = standings["Alice Angler"]
        assert (alice["events"], alice["firsts"], alice["seconds"], alice["thirds"]) == (3, 3, 0, 0)
        assert alice["top3"] == 3

        bob = standings["Bob Angler"]
        assert (bob["events"], bob["firsts"], bob["seconds"], bob["thirds"]) == (3, 1, 2, 0)

        frank = standings["Frank Angler"]
        assert (frank["events"], frank["firsts"], frank["seconds"], frank["thirds"]) == (3, 0, 0, 3)
        assert frank["top3"] == 3

    def test_fish_and_weight_credit_the_whole_boat(self, season_2026):
        standings = {row["name"]: row for row in _boards("angler")["standings"]}
        # Alice: 5 + 5 + 5 fish, 20.00 + 18.00 + 22.00 lbs.
        assert standings["Alice Angler"]["total_fish"] == 15
        assert standings["Alice Angler"]["total_weight"] == pytest.approx(60.00)
        # Dana: 4 + 4 + 5 fish, 15.00 + 12.00 + 22.00 lbs.
        assert standings["Dana Angler"]["total_fish"] == 13
        assert standings["Dana Angler"]["total_weight"] == pytest.approx(49.00)
        # Erin never left 3rd: 3 + 2 + 3 fish, 10.00 + 8.00 + 9.00 lbs.
        assert standings["Erin Angler"]["total_fish"] == 8
        assert standings["Erin Angler"]["total_weight"] == pytest.approx(27.00)

    def test_single_event_records_per_angler(self, season_2026):
        standings = {row["name"]: row for row in _boards("angler")["standings"]}
        assert standings["Alice Angler"]["best_stringer"] == pytest.approx(22.00)
        assert standings["Alice Angler"]["best_bass"] == pytest.approx(6.00)
        assert standings["Bob Angler"]["best_stringer"] == pytest.approx(20.00)
        assert standings["Bob Angler"]["best_bass"] == pytest.approx(5.50)

    def test_money_split_fifty_fifty_with_rollover(self, season_2026):
        result = _boards("angler")
        money = {row["name"]: row["money"] for row in result["standings"]}
        assert money["Alice Angler"] == pytest.approx(126.00)
        assert money["Dana Angler"] == pytest.approx(96.00)
        assert money["Bob Angler"] == pytest.approx(84.00)
        assert money["Carl Angler"] == pytest.approx(72.00)
        assert money["Erin Angler"] == pytest.approx(36.00)
        assert money["Frank Angler"] == pytest.approx(36.00)
        # Every dollar paid to a boat reaches exactly one angler board.
        assert sum(money.values()) == pytest.approx(450.00)
        assert float(result["total_paid"]) == pytest.approx(450.00)

    def test_board_ordering_and_zero_rows_dropped(self, season_2026):
        boards = _boards("angler")["boards"]

        assert [r["name"] for r in boards["wins"]][0] == "Alice Angler"
        assert boards["wins"][0]["firsts"] == 3
        # Bob, Carl and Dana each won once; Erin and Frank never did and so
        # must not appear on a "most wins" board at all.
        assert len(boards["wins"]) == 4
        assert "Erin Angler" not in [r["name"] for r in boards["wins"]]

        assert [r["name"] for r in boards["money"]][0] == "Alice Angler"
        assert [r["name"] for r in boards["weight"]][0] == "Alice Angler"
        assert [r["name"] for r in boards["fish"]][0] == "Alice Angler"
        # Nobody took 2nd three times, but three anglers took it twice.
        assert boards["seconds"][0]["seconds"] == 2
        assert boards["thirds"][0]["thirds"] == 3

    def test_tied_rows_share_a_rank(self, season_2026):
        """Bob, Carl and Dana are identical on (seconds, firsts) but not on
        weight, so the 2nd-place board separates them; the thirds board ties
        Erin and Frank, who are identical on every key."""
        boards = _boards("angler")["boards"]
        thirds = {row["name"]: row for row in boards["thirds"]}
        assert thirds["Erin Angler"]["rank"] == thirds["Frank Angler"]["rank"] == 1
        assert thirds["Frank Angler"]["tied"] is True


class TestTeamSeasonBoards:
    """Per-pairing boards answer "which boat did best together"."""

    def test_pairings_are_identified_independent_of_seat(self, season_2026):
        standings = {row["team_name"]: row for row in _boards("team")["standings"]}
        # Nine boats fished, but Erin & Frank stayed together all three
        # events, so seven distinct pairings appear.
        assert len(standings) == 7
        assert standings["Erin Angler & Frank Angler"]["events"] == 3
        assert standings["Alice Angler & Bob Angler"]["events"] == 1
        # Alice sat in seat 1 of every boat she fished and Carl in seat 2 of
        # one and seat 1 of another; the pairing key must not care.
        assert standings["Alice Angler & Carl Angler"]["events"] == 1
        assert standings["Bob Angler & Carl Angler"]["events"] == 1

    def test_full_boat_amount_not_split(self, season_2026):
        standings = {row["team_name"]: row for row in _boards("team")["standings"]}
        assert standings["Alice Angler & Bob Angler"]["money"] == pytest.approx(84.00)
        assert standings["Alice Angler & Dana Angler"]["money"] == pytest.approx(108.00)
        # Three third-place finishes at $24 each.
        assert standings["Erin Angler & Frank Angler"]["money"] == pytest.approx(72.00)

    def test_season_long_pairing_leads_weight_and_fish(self, season_2026):
        """The grain genuinely differs: Erin & Frank never beat a single boat,
        but three events together out-total every one-off pairing."""
        boards = _boards("team")["boards"]
        assert boards["weight"][0]["team_name"] == "Erin Angler & Frank Angler"
        assert boards["weight"][0]["total_weight"] == pytest.approx(27.00)
        assert boards["fish"][0]["team_name"] == "Erin Angler & Frank Angler"
        assert boards["wins"][0]["team_name"] == "Alice Angler & Dana Angler"
        assert boards["wins"][0]["firsts"] == 1


def _add_team_tournament(
    db_session: Session, event_date: date, boats: List[Tuple[Angler, Angler, str, int]]
) -> None:
    """One complete 2026 team-format tournament: ``(boater, non-boater, weight, place)``."""
    event = Event(
        date=event_date, year=2026, name=f"Event {event_date}", event_type="sabc_tournament"
    )
    db_session.add(event)
    db_session.commit()
    tournament = Tournament(
        event_id=event.id,
        name=event.name,
        fish_limit=5,
        entry_fee=Decimal("50.00"),
        is_team=True,
        complete=True,
        aoy_points=False,
        limit_type="boat",
    )
    db_session.add(tournament)
    db_session.commit()
    for boater, non_boater, weight, place in boats:
        db_session.add(
            TeamResult(
                tournament_id=tournament.id,
                angler1_id=boater.id,
                angler2_id=non_boater.id,
                num_fish=5,
                total_weight=Decimal(weight),
                big_bass_weight=Decimal("5.50"),
                place_finish=place,
            )
        )
    db_session.commit()


@pytest.fixture
def zed_and_amy(db_session: Session) -> Tuple[Angler, Angler]:
    """Two members whose names sort opposite to Zed-boats, Amy-rides."""
    zed = Angler(name="Zed Angler", email="zed@example.com", member=True)
    amy = Angler(name="Amy Angler", email="amy@example.com", member=True)
    db_session.add_all([zed, amy])
    db_session.commit()
    return zed, amy


def _team_standings() -> List[Dict[str, Any]]:
    return cast(List[Dict[str, Any]], _boards("team")["standings"])


class TestTeamNamesListBoaterFirst:
    """A team is shown as "Boater & Non-boater", not alphabetically."""

    def test_season_boards_put_boater_first(self, db_session: Session, zed_and_amy):
        zed, amy = zed_and_amy
        _add_team_tournament(db_session, date(2026, 3, 14), [(zed, amy, "20.00", 1)])
        standings = _team_standings()
        assert [row["team_name"] for row in standings] == ["Zed Angler & Amy Angler"]

    def test_single_event_records_put_boater_first(self, db_session: Session, zed_and_amy):
        zed, amy = zed_and_amy
        _add_team_tournament(db_session, date(2026, 3, 14), [(zed, amy, "20.00", 1)])
        with engine.connect() as conn:
            qs = QueryService(conn)
            stringer = qs.fetch_all(get_team_heavy_stringer_query(), {"year": 2026})
            bass = qs.fetch_all(get_team_big_bass_query(), {"year": 2026})
        assert stringer[0]["team_name"] == "Zed Angler & Amy Angler"
        assert bass[0]["team_name"] == "Zed Angler & Amy Angler"

    def test_swapping_seats_mid_season_stays_one_pairing(self, db_session: Session, zed_and_amy):
        """Same two anglers, boater role swapped: still one row, so the
        earnings join (keyed per pairing) is not duplicated."""
        zed, amy = zed_and_amy
        _add_team_tournament(db_session, date(2026, 3, 14), [(zed, amy, "20.00", 1)])
        _add_team_tournament(db_session, date(2026, 4, 11), [(amy, zed, "18.00", 1)])
        standings = _team_standings()
        assert len(standings) == 1
        assert standings[0]["events"] == 2
        assert standings[0]["team_name"] in ("Zed Angler & Amy Angler", "Amy Angler & Zed Angler")


class TestPlaceMoneyTies:
    """A RANK() tie seats two boats in one place and skips the next."""

    def test_tied_places_pool_and_split_their_slots(self):
        boats = [
            {"place_finish": 1, "total_weight": Decimal("20.00")},
            {"place_finish": 1, "total_weight": Decimal("20.00")},
            {"place_finish": 3, "total_weight": Decimal("15.00")},
            {"place_finish": 4, "total_weight": Decimal("10.00")},
        ]
        awards = _award_place_money(boats, boat_count=4)
        # 1st + 2nd money ($80 + $56) pooled between the tied boats.
        assert awards[0] == awards[1] == Decimal("68.00")
        assert awards[2] == Decimal("32.00")  # 3rd place, $8 x 4 boats
        assert 3 not in awards
        # The tie must not change what the tournament paid out in total.
        assert sum(awards.values()) == sum(p * 4 for p in PLACE_PAYOUTS_PER_BOAT)

    def test_boats_that_weighed_nothing_take_no_place_money(self):
        boats = [
            {"place_finish": 1, "total_weight": Decimal("12.00")},
            {"place_finish": 2, "total_weight": Decimal("0")},
        ]
        awards = _award_place_money(boats, boat_count=2)
        assert awards == {0: Decimal("40.00")}


class TestAwardsPageRendering:
    """The page renders both grains for 2026 and is untouched before it."""

    def test_team_format_page_shows_both_grains(self, client: TestClient, season_2026):
        response = client.get("/awards/2026")
        assert response.status_code == 200
        body = response.text
        for heading in (
            "Most Wins",
            "Most Top-3 Finishes",
            "Most Money Won",
            "Highest Total Weight",
            "Most Fish Caught",
            "Most 2nd Place Finishes",
            "Most 3rd Place Finishes",
            "Big Stringer of the Year",
            "Big Bass of the Year",
        ):
            assert heading in body, f"missing board: {heading}"
        assert "By Angler" in body and "By Team" in body
        assert "Angler Season Standings" in body
        assert "Team Season Standings" in body
        # Season payout total and a known angler total both reach the page.
        assert "$450.00" in body
        assert "$126.00" in body

    def test_pre_2026_page_is_unchanged(self, client: TestClient, season_2026, season_2025_event):
        """2025 keeps the individual-format layout: AOY, no grain tabs."""
        response = client.get("/awards/2025")
        assert response.status_code == 200
        body = response.text
        assert "Angler of the Year" in body
        assert "By Angler" not in body
        assert "Most Money Won" not in body
        assert "Season Payout" not in body
