"""Unit tests for profile query functions.

Tests SQL query string generation for user profile statistics.
"""

from routes.auth.profile_queries import (
    all_time_finishes_query,
    aoy_position_query,
    best_weight_query,
    big_bass_query,
    current_finishes_query,
    tournaments_count_query,
)


class TestProfileQueries:
    """Test profile query string generation."""

    def test_tournaments_count_query(self):
        """Test tournaments count query returns valid SQL."""
        query = tournaments_count_query()
        assert "COUNT(DISTINCT t.id)" in query
        assert "FROM results r" in query
        assert "WHERE r.angler_id = :user_id" in query
        assert "disqualified = FALSE" in query

    def test_best_weight_query(self):
        """Test best weight query returns valid SQL."""
        query = best_weight_query()
        assert "MAX(r.total_weight" in query
        assert "dead_fish_penalty" in query
        assert "WHERE r.angler_id = :user_id" in query
        assert "disqualified = FALSE" in query

    def test_big_bass_query(self):
        """Test big bass query returns valid SQL."""
        query = big_bass_query()
        assert "MAX(r.big_bass_weight)" in query
        assert "FROM results r" in query
        assert "WHERE r.angler_id = :user_id" in query
        assert "disqualified = FALSE" in query

    def test_current_finishes_query(self):
        """Test current year finishes query returns valid SQL."""
        query = current_finishes_query()
        assert "SUM(CASE WHEN place = 1 THEN 1 ELSE 0 END) as first" in query
        assert "SUM(CASE WHEN place = 2 THEN 1 ELSE 0 END) as second" in query
        assert "SUM(CASE WHEN place = 3 THEN 1 ELSE 0 END) as third" in query
        assert "ROW_NUMBER()" in query
        assert "WHERE (tr.angler1_id = :user_id OR tr.angler2_id = :user_id)" in query
        assert "e.year = :current_year" in query

    def test_all_time_finishes_query(self):
        """Test all-time finishes query returns valid SQL."""
        query = all_time_finishes_query()
        assert "SUM(CASE WHEN place = 1 THEN 1 ELSE 0 END) as first" in query
        assert "SUM(CASE WHEN place = 2 THEN 1 ELSE 0 END) as second" in query
        assert "SUM(CASE WHEN place = 3 THEN 1 ELSE 0 END) as third" in query
        assert "ROW_NUMBER()" in query
        assert "WHERE (tr.angler1_id = :user_id OR tr.angler2_id = :user_id)" in query
        assert "e.year >= 2022" in query

    def test_aoy_position_query(self):
        """Test AOY position query returns valid SQL."""
        query = aoy_position_query()
        assert "WITH tournament_standings AS" in query
        assert "points_calc AS" in query
        assert "aoy_standings AS" in query
        assert "DENSE_RANK()" in query
        assert "101 - place_finish" in query
        assert "WHERE a.member = TRUE" in query
        assert "WHERE id = :user_id" in query
        assert "e.year = :current_year" in query
