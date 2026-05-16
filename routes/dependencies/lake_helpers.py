"""Lake and ramp database helper functions."""

from typing import Any, Dict, List, Optional

from core.db_schema import engine
from core.query_service import QueryService


def find_lake_by_id(lake_id: int, field: str = "name") -> Optional[str]:
    """Find a lake by ID and return a specific field.

    Note: 'name' field maps to 'display_name' in the database.
    """
    with engine.connect() as conn:
        qs = QueryService(conn)
        lake = qs.get_lake_by_id(lake_id)
        if not lake:
            return None

        # Map 'name' to 'display_name' for backwards compatibility
        if field == "name":
            return lake.get("display_name")

        return lake.get(field)


def get_lakes_list(with_ramps: bool = False) -> List[Dict[str, Any]]:
    """Get list of all lakes.

    Args:
        with_ramps: When True, each lake dict includes a ``ramps`` key
            populated via a single LEFT JOIN. This avoids the
            ``1 + N_lakes`` connection-per-request pattern that callers
            previously used (``[get_ramps_for_lake(l["id"]) for l in
            get_lakes_list()]``).
    """
    with engine.connect() as conn:
        qs = QueryService(conn)
        if not with_ramps:
            return qs.get_lakes_list()

        # Single LEFT JOIN: pulls all lakes and their ramps in one round trip.
        # Columns listed explicitly (rather than ``l.*``/``r.*``) so we control
        # the alias mapping and don't blow up if schemas evolve.
        rows = qs.fetch_all(
            """
            SELECT l.id           AS lake_id,
                   l.yaml_key     AS lake_yaml_key,
                   l.display_name AS lake_display_name,
                   l.google_maps_iframe AS lake_google_maps_iframe,
                   r.id           AS ramp_id,
                   r.name         AS ramp_name,
                   r.google_maps_iframe AS ramp_google_maps_iframe
            FROM lakes l
            LEFT JOIN ramps r ON r.lake_id = l.id
            ORDER BY l.display_name, r.name
            """
        )

        lakes_by_id: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            lake_id = row["lake_id"]
            lake = lakes_by_id.get(lake_id)
            if lake is None:
                lake = {
                    "id": lake_id,
                    "yaml_key": row.get("lake_yaml_key"),
                    "display_name": row.get("lake_display_name"),
                    "google_maps_iframe": row.get("lake_google_maps_iframe"),
                    "ramps": [],
                }
                lakes_by_id[lake_id] = lake
            if row.get("ramp_id") is not None:
                lake["ramps"].append(
                    {
                        "id": row["ramp_id"],
                        "name": row.get("ramp_name"),
                        "lake_id": lake_id,
                        "google_maps_iframe": row.get("ramp_google_maps_iframe"),
                    }
                )

        # Preserve the same display_name ordering as ``get_lakes_list()``.
        return list(lakes_by_id.values())


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
