"""Lake and ramp database helper functions."""

from typing import Any, Dict, List, Optional

from core.db_schema import engine
from core.query_service import QueryService


def find_lake_by_id(lake_id: int, field: str = "name") -> Optional[str]:
    """Find a lake by ID and return a specific field."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        lake = qs.get_lake_by_id(lake_id)
        if not lake:
            return None
        return lake.get(field, lake["name"]) if field != "name" else lake["name"]


def get_lakes_list() -> List[Dict[str, Any]]:
    """Get list of all lakes."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_lakes_list()


def find_ramp_name_by_id(ramp_id: int) -> Optional[str]:
    """Find a ramp name by ID."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        ramp = qs.get_ramp_by_id(ramp_id)
        return ramp["name"] if ramp else None


def get_all_ramps() -> List[Dict[str, Any]]:
    """Get all ramps ordered by name."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.fetch_all("SELECT * FROM ramps ORDER BY name")


def get_ramps_for_lake(lake_id: int) -> List[Dict[str, Any]]:
    """Get all ramps for a specific lake."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_ramps_for_lake(lake_id)


def validate_lake_ramp_combo(lake_id: int, ramp_id: int) -> bool:
    """Validate that a ramp belongs to a lake."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.validate_lake_ramp_combo(lake_id, ramp_id)
