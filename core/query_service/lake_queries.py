from typing import Any, Dict, List, Optional

from core.query_service.base import QueryServiceBase


class LakeQueries(QueryServiceBase):
    def get_lakes_list(self) -> List[Dict[str, Any]]:
        return self.fetch_all("SELECT * FROM lakes ORDER BY display_name")

    def get_lake_by_id(self, lake_id: int) -> Optional[Dict[str, Any]]:
        return self.fetch_one("SELECT * FROM lakes WHERE id = :id", {"id": lake_id})

    def get_ramps_for_lake(self, lake_id: int) -> List[Dict[str, Any]]:
        return self.fetch_all(
            "SELECT * FROM ramps WHERE lake_id = :lake_id ORDER BY name", {"lake_id": lake_id}
        )

    def get_ramp_by_id(self, ramp_id: int) -> Optional[Dict[str, Any]]:
        return self.fetch_one("SELECT * FROM ramps WHERE id = :id", {"id": ramp_id})

    def validate_lake_ramp_combo(self, lake_id: int, ramp_id: int) -> bool:
        result = self.fetch_value(
            "SELECT COUNT(*) FROM ramps WHERE id = :ramp_id AND lake_id = :lake_id",
            {"ramp_id": ramp_id, "lake_id": lake_id},
        )
        return result > 0
