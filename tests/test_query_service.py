"""Tests for QueryService."""

from sqlalchemy import text

from core.query_service import QueryService


class TestQueryService:
    """Test QueryService database operations."""

    def test_fetch_all(self, db_conn):
        """Test fetch_all returns list of dicts."""
        # Insert test data
        db_conn.execute(
            text(
                "INSERT INTO anglers (name, email) VALUES ('User 1', 'user1@test.com'), ('User 2', 'user2@test.com')"
            ),
        )
        db_conn.commit()

        qs = QueryService(db_conn)
        results = qs.fetch_all("SELECT name, email FROM anglers ORDER BY name")

        assert len(results) == 2
        assert results[0]["name"] == "User 1"
        assert results[0]["email"] == "user1@test.com"
        assert results[1]["name"] == "User 2"

    def test_fetch_one(self, db_conn):
        """Test fetch_one returns single dict."""
        db_conn.execute(
            text("INSERT INTO anglers (name, email) VALUES ('Test User', 'test@test.com')"),
        )
        db_conn.commit()

        qs = QueryService(db_conn)
        result = qs.fetch_one(
            "SELECT name, email FROM anglers WHERE email = :email", {"email": "test@test.com"}
        )

        assert result is not None
        assert result["name"] == "Test User"
        assert result["email"] == "test@test.com"

    def test_fetch_one_not_found(self, db_conn):
        """Test fetch_one returns None when no results."""
        qs = QueryService(db_conn)
        result = qs.fetch_one(
            "SELECT * FROM anglers WHERE email = :email", {"email": "notfound@test.com"}
        )

        assert result is None

    def test_fetch_value(self, db_conn):
        """Test fetch_value returns single value."""
        db_conn.execute(
            text("INSERT INTO anglers (name, email) VALUES ('Test User', 'test@test.com')")
        )
        db_conn.commit()

        qs = QueryService(db_conn)
        name = qs.fetch_value(
            "SELECT name FROM anglers WHERE email = :email", {"email": "test@test.com"}
        )

        assert name == "Test User"


class TestUpsertResult:
    """Test tournament result upsert functionality."""

    def test_upsert_result_insert(self, db_conn, tournament_data, member_user):
        """Test inserting a new result."""
        qs = QueryService(db_conn)

        # Insert new result
        qs.upsert_result(
            tournament_id=tournament_data["tournament_id"],
            angler_id=member_user["id"],
            num_fish=5,
            total_weight=12.5,
            big_bass_weight=3.2,
            dead_fish_penalty=0.5,
            disqualified=False,
            buy_in=False,
        )
        db_conn.commit()

        # Verify result was inserted
        result = qs.fetch_one(
            "SELECT * FROM results WHERE tournament_id = :tid AND angler_id = :aid",
            {"tid": tournament_data["tournament_id"], "aid": member_user["id"]},
        )

        assert result is not None
        assert result["num_fish"] == 5
        assert float(result["total_weight"]) == 12.5
        assert float(result["big_bass_weight"]) == 3.2
        assert float(result["dead_fish_penalty"]) == 0.5
        assert result["disqualified"] is False
        assert result["buy_in"] is False

    def test_upsert_result_update(self, db_conn, tournament_data, member_user):
        """Test updating an existing result."""
        qs = QueryService(db_conn)

        # Insert initial result
        qs.upsert_result(
            tournament_id=tournament_data["tournament_id"],
            angler_id=member_user["id"],
            num_fish=3,
            total_weight=8.0,
        )
        db_conn.commit()

        # Update result
        qs.upsert_result(
            tournament_id=tournament_data["tournament_id"],
            angler_id=member_user["id"],
            num_fish=5,
            total_weight=12.5,
            big_bass_weight=3.2,
        )
        db_conn.commit()

        # Verify result was updated, not duplicated
        results = qs.fetch_all(
            "SELECT * FROM results WHERE tournament_id = :tid AND angler_id = :aid",
            {"tid": tournament_data["tournament_id"], "aid": member_user["id"]},
        )

        assert len(results) == 1  # Only one result, not two
        assert results[0]["num_fish"] == 5
        assert float(results[0]["total_weight"]) == 12.5
        assert float(results[0]["big_bass_weight"]) == 3.2

    def test_upsert_result_multiple_anglers(
        self, db_conn, tournament_data, member_user, admin_user
    ):
        """Test upserting results for multiple anglers."""
        qs = QueryService(db_conn)

        # Insert result for member
        qs.upsert_result(
            tournament_id=tournament_data["tournament_id"],
            angler_id=member_user["id"],
            num_fish=5,
            total_weight=12.5,
        )

        # Insert result for admin
        qs.upsert_result(
            tournament_id=tournament_data["tournament_id"],
            angler_id=admin_user["id"],
            num_fish=4,
            total_weight=10.0,
        )
        db_conn.commit()

        # Verify both results exist
        results = qs.fetch_all(
            "SELECT * FROM results WHERE tournament_id = :tid ORDER BY total_weight DESC",
            {"tid": tournament_data["tournament_id"]},
        )

        assert len(results) == 2
        assert results[0]["angler_id"] == member_user["id"]
        assert results[1]["angler_id"] == admin_user["id"]

    def test_upsert_result_with_flags(self, db_conn, tournament_data, member_user):
        """Test upserting result with disqualified and buy_in flags."""
        qs = QueryService(db_conn)

        # Insert result with flags
        qs.upsert_result(
            tournament_id=tournament_data["tournament_id"],
            angler_id=member_user["id"],
            num_fish=0,
            total_weight=0.0,
            disqualified=True,
            buy_in=False,
        )
        db_conn.commit()

        result = qs.fetch_one(
            "SELECT * FROM results WHERE tournament_id = :tid AND angler_id = :aid",
            {"tid": tournament_data["tournament_id"], "aid": member_user["id"]},
        )

        assert result["disqualified"] is True
        assert result["buy_in"] is False

        # Update to buy-in
        qs.upsert_result(
            tournament_id=tournament_data["tournament_id"],
            angler_id=member_user["id"],
            num_fish=0,
            total_weight=0.0,
            disqualified=False,
            buy_in=True,
        )
        db_conn.commit()

        result = qs.fetch_one(
            "SELECT * FROM results WHERE tournament_id = :tid AND angler_id = :aid",
            {"tid": tournament_data["tournament_id"], "aid": member_user["id"]},
        )

        assert result["disqualified"] is False
        assert result["buy_in"] is True
