"""Smoke tests for v_angler_tournament_results and v_team_tournament_results.

The views are designed to be format-agnostic readers — they project both the
``results`` and ``team_results`` tables into a single shape so reader code
doesn't have to know whether a tournament is individual- or team-format.

This file verifies:
1. Both views materialize correctly under the SQLite test fixture (and via
   the same DDL Postgres runs in production).
2. The Admin User exclusion fires on every UNION branch.
3. The NOT EXISTS guards prevent double-counting when both tables are
   populated for the same (tournament, angler) pair.
4. The team-format fallback path (project team_results onto angler1, zero
   onto angler2) behaves as documented.

No reader code is migrated yet — see Phase 10 audit notes for the follow-up
plan that points each ~30 reader site at one of these views.
"""

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.db_schema import Angler, Result, TeamResult, Tournament


def _dec(value: object) -> Decimal:
    """Coerce a SQLite-returned numeric (float, int, or Decimal) to Decimal
    so equality comparisons work uniformly. Tests use SQLite with a Decimal
    adapter that stores as float (see conftest.py:set_sqlite_decimal_support),
    so view-projected numerics come back as floats here."""
    return Decimal(str(value))


@pytest.fixture
def admin_angler(db_session: Session) -> Angler:
    """The 'Admin User' seed account that the views must exclude."""
    angler = Angler(name="Admin User", email="admin@example.com", member=True, is_admin=True)
    db_session.add(angler)
    db_session.commit()
    db_session.refresh(angler)
    return angler


@pytest.fixture
def alice(db_session: Session) -> Angler:
    angler = Angler(name="Alice Angler", email="alice@example.com", member=True)
    db_session.add(angler)
    db_session.commit()
    db_session.refresh(angler)
    return angler


@pytest.fixture
def bob(db_session: Session) -> Angler:
    angler = Angler(name="Bob Boatmate", email="bob@example.com", member=True)
    db_session.add(angler)
    db_session.commit()
    db_session.refresh(angler)
    return angler


class TestAnglerViewShape:
    """v_angler_tournament_results returns one row per (tournament, angler)
    regardless of whether the data lives in results, team_results, or both."""

    def test_view_exists_and_returns_empty(self, db_session: Session):
        """View materializes and returns no rows when both tables are empty."""
        rows = db_session.execute(text("SELECT * FROM v_angler_tournament_results")).fetchall()
        assert rows == []

    def test_individual_format_returns_results_row(
        self, db_session: Session, test_tournament: Tournament, alice: Angler
    ):
        """Individual-format: one row per angler, sourced from `results`."""
        db_session.add(
            Result(
                tournament_id=test_tournament.id,
                angler_id=alice.id,
                num_fish=5,
                total_weight=Decimal("12.34"),
                big_bass_weight=Decimal("4.50"),
                disqualified=False,
                buy_in=False,
                was_member=True,
            )
        )
        db_session.commit()

        rows = (
            db_session.execute(text("SELECT * FROM v_angler_tournament_results ORDER BY angler_id"))
            .mappings()
            .all()
        )
        assert len(rows) == 1
        assert rows[0]["angler_id"] == alice.id
        assert _dec(rows[0]["total_weight"]) == Decimal("12.34")
        assert _dec(rows[0]["big_bass_weight"]) == Decimal("4.50")
        assert rows[0]["source"] == "results"

    def test_team_format_fallback_credits_angler1(
        self,
        db_session: Session,
        test_team_format_tournament: Tournament,
        alice: Angler,
        bob: Angler,
    ):
        """Team-format without individual results: project team_results onto
        angler1 with full credit, angler2 gets a zero-stats row so totals
        don't double-count but participation still registers."""
        db_session.add(
            TeamResult(
                tournament_id=test_team_format_tournament.id,
                angler1_id=alice.id,
                angler2_id=bob.id,
                num_fish=8,
                total_weight=Decimal("22.50"),
                big_bass_weight=Decimal("6.25"),
                place_finish=1,
            )
        )
        db_session.commit()

        rows = (
            db_session.execute(text("SELECT * FROM v_angler_tournament_results ORDER BY angler_id"))
            .mappings()
            .all()
        )
        assert len(rows) == 2

        by_angler = {r["angler_id"]: r for r in rows}
        # Alice (angler1) carries the full team weight.
        assert _dec(by_angler[alice.id]["total_weight"]) == Decimal("22.50")
        assert _dec(by_angler[alice.id]["big_bass_weight"]) == Decimal("6.25")
        assert by_angler[alice.id]["num_fish"] == 8
        assert by_angler[alice.id]["source"] == "team_angler1"
        # Bob (angler2) gets a zero row so participation counts.
        assert _dec(by_angler[bob.id]["total_weight"]) == Decimal("0")
        assert by_angler[bob.id]["num_fish"] == 0
        assert by_angler[bob.id]["source"] == "team_angler2"

    def test_no_double_count_when_both_tables_populated(
        self,
        db_session: Session,
        test_tournament: Tournament,
        alice: Angler,
    ):
        """When both `results` AND `team_results` have rows for the same
        angler, the view returns only the `results` row — the NOT EXISTS
        guard in the team_angler1 branch suppresses the duplicate."""
        db_session.add(
            Result(
                tournament_id=test_tournament.id,
                angler_id=alice.id,
                num_fish=5,
                total_weight=Decimal("12.34"),
                big_bass_weight=Decimal("4.50"),
            )
        )
        db_session.add(
            TeamResult(
                tournament_id=test_tournament.id,
                angler1_id=alice.id,
                angler2_id=None,
                num_fish=5,
                total_weight=Decimal("12.34"),
                big_bass_weight=Decimal("4.50"),
                place_finish=1,
            )
        )
        db_session.commit()

        rows = (
            db_session.execute(
                text("SELECT * FROM v_angler_tournament_results WHERE angler_id = :aid"),
                {"aid": alice.id},
            )
            .mappings()
            .all()
        )
        assert len(rows) == 1
        assert rows[0]["source"] == "results"

    def test_admin_user_excluded(
        self,
        db_session: Session,
        test_tournament: Tournament,
        admin_angler: Angler,
        alice: Angler,
    ):
        """The view drops every row for the seed 'Admin User' angler."""
        db_session.add_all(
            [
                Result(
                    tournament_id=test_tournament.id,
                    angler_id=alice.id,
                    num_fish=5,
                    total_weight=Decimal("10.0"),
                ),
                Result(
                    tournament_id=test_tournament.id,
                    angler_id=admin_angler.id,
                    num_fish=99,
                    total_weight=Decimal("999.0"),
                ),
            ]
        )
        db_session.commit()

        rows = db_session.execute(text("SELECT angler_id FROM v_angler_tournament_results")).all()
        angler_ids = {row[0] for row in rows}
        assert alice.id in angler_ids
        assert admin_angler.id not in angler_ids


class TestTeamViewShape:
    """v_team_tournament_results returns one row per boat per tournament."""

    def test_view_exists_and_returns_empty(self, db_session: Session):
        rows = db_session.execute(text("SELECT * FROM v_team_tournament_results")).fetchall()
        assert rows == []

    def test_team_results_row_is_canonical(
        self,
        db_session: Session,
        test_team_format_tournament: Tournament,
        alice: Angler,
        bob: Angler,
    ):
        """When team_results has a row, it's the source — not the per-angler
        results rows."""
        db_session.add(
            TeamResult(
                tournament_id=test_team_format_tournament.id,
                angler1_id=alice.id,
                angler2_id=bob.id,
                num_fish=10,
                total_weight=Decimal("30.0"),
                big_bass_weight=Decimal("8.0"),
                place_finish=1,
            )
        )
        db_session.commit()

        rows = db_session.execute(text("SELECT * FROM v_team_tournament_results")).mappings().all()
        assert len(rows) == 1
        assert rows[0]["angler1_id"] == alice.id
        assert rows[0]["angler2_id"] == bob.id
        assert _dec(rows[0]["total_weight"]) == Decimal("30.0")
        assert rows[0]["place_finish"] == 1
        assert rows[0]["source"] == "team_results"

    def test_individual_results_synthesize_solo_team(
        self,
        db_session: Session,
        test_tournament: Tournament,
        alice: Angler,
    ):
        """Individual-format without a team_results row: each angler becomes
        a 'boat of one' (angler2_id = NULL)."""
        db_session.add(
            Result(
                tournament_id=test_tournament.id,
                angler_id=alice.id,
                num_fish=3,
                total_weight=Decimal("8.5"),
                big_bass_weight=Decimal("3.0"),
            )
        )
        db_session.commit()

        rows = db_session.execute(text("SELECT * FROM v_team_tournament_results")).mappings().all()
        assert len(rows) == 1
        assert rows[0]["angler1_id"] == alice.id
        assert rows[0]["angler2_id"] is None
        assert _dec(rows[0]["total_weight"]) == Decimal("8.5")
        assert rows[0]["place_finish"] is None
        assert rows[0]["source"] == "results"

    def test_disqualified_and_buy_in_excluded_from_synthetic_boats(
        self,
        db_session: Session,
        test_tournament: Tournament,
        alice: Angler,
        bob: Angler,
    ):
        """Disqualified or buy-in results don't synthesize boats (they'd
        skew rankings). Real team_results rows are unaffected."""
        db_session.add_all(
            [
                Result(
                    tournament_id=test_tournament.id,
                    angler_id=alice.id,
                    num_fish=0,
                    total_weight=Decimal("0"),
                    disqualified=True,
                ),
                Result(
                    tournament_id=test_tournament.id,
                    angler_id=bob.id,
                    num_fish=0,
                    total_weight=Decimal("0"),
                    buy_in=True,
                ),
            ]
        )
        db_session.commit()

        rows = db_session.execute(text("SELECT * FROM v_team_tournament_results")).fetchall()
        assert rows == []

    def test_admin_user_excluded_from_team_view(
        self,
        db_session: Session,
        test_team_format_tournament: Tournament,
        admin_angler: Angler,
        alice: Angler,
        bob: Angler,
    ):
        """A team_results row whose angler1 or angler2 is the Admin User is
        suppressed entirely from the view."""
        db_session.add_all(
            [
                TeamResult(
                    tournament_id=test_team_format_tournament.id,
                    angler1_id=alice.id,
                    angler2_id=bob.id,
                    num_fish=5,
                    total_weight=Decimal("15.0"),
                ),
                TeamResult(
                    tournament_id=test_team_format_tournament.id,
                    angler1_id=admin_angler.id,
                    angler2_id=alice.id,
                    num_fish=99,
                    total_weight=Decimal("999.0"),
                ),
            ]
        )
        db_session.commit()

        rows = (
            db_session.execute(text("SELECT angler1_id, angler2_id FROM v_team_tournament_results"))
            .mappings()
            .all()
        )
        # Only the alice+bob team should appear; the admin-paired team is dropped.
        assert len(rows) == 1
        assert rows[0]["angler1_id"] == alice.id
        assert rows[0]["angler2_id"] == bob.id
