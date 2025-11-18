"""Unit tests for home page query functions.

Tests SQL query string generation for home page data.
"""

from routes.pages.home_queries import get_top_results_query, get_tournaments_query


class TestHomePageQueries:
    """Test home page query string generation."""

    def test_get_tournaments_query(self):
        """Test tournaments query returns valid SQL."""
        query = get_tournaments_query()
        assert "SELECT t.id, e.date, e.name" in query
        assert "FROM tournaments t" in query
        assert "JOIN events e ON t.event_id = e.id" in query
        assert "LEFT JOIN lakes l ON t.lake_id = l.id" in query
        assert "LEFT JOIN ramps ra ON t.ramp_id = ra.id" in query
        assert "LEFT JOIN results r ON t.id = r.tournament_id" in query
        assert "GROUP BY t.id" in query
        assert "ORDER BY e.date DESC" in query
        assert "LIMIT :limit OFFSET :offset" in query
        assert "total_anglers" in query
        assert "total_fish" in query
        assert "total_weight" in query

    def test_get_top_results_query(self):
        """Test top results query returns valid SQL."""
        query = get_top_results_query()
        assert "SELECT" in query
        assert "tr.place_finish" in query
        assert "a1.name as angler1_name" in query
        assert "a2.name as angler2_name" in query
        assert "tr.total_weight" in query
        assert "FROM team_results tr" in query
        assert "JOIN anglers a1 ON tr.angler1_id = a1.id" in query
        assert "LEFT JOIN anglers a2 ON tr.angler2_id = a2.id" in query
        assert "WHERE tr.tournament_id = :tournament_id" in query
        assert "ORDER BY tr.place_finish ASC" in query
        assert "LIMIT 3" in query
        assert "Admin User" in query
