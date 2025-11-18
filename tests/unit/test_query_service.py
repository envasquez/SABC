"""Query service tests."""

from core.query_service import QueryService


class TestQueryService:
    """Test query service methods."""

    def test_query_service_init(self):
        """Test query service initialization."""
        qs = QueryService()
        assert qs is not None

    def test_fetch_all_empty(self):
        """Test fetch_all with no results."""
        qs = QueryService()
        results = qs.fetch_all("SELECT 1 WHERE 1=0", {})
        assert results == []

    def test_fetch_one_empty(self):
        """Test fetch_one with no results."""
        qs = QueryService()
        result = qs.fetch_one("SELECT 1 WHERE 1=0", {})
        assert result is None
