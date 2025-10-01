"""Lake-related methods for query service facade."""

from typing import Any, Dict, List, Optional

from sqlalchemy import Connection

from core.services.lake_service import LakeService
from core.services.query_facade_user import QueryFacadeUser


class QueryFacadeLake(QueryFacadeUser):
    """Lake query delegation methods."""

    def __init__(self, conn: Connection):
        super().__init__(conn)
        self._lake_service = LakeService(conn)

    def get_lakes_list(self) -> List[Dict[str, Any]]:
        return self._lake_service.get_lakes_list()

    def get_lake_by_id(self, lake_id: int) -> Optional[dict]:
        return self._lake_service.get_lake_by_id(lake_id)

    def get_ramps_for_lake(self, lake_id: int) -> list[dict]:
        return self._lake_service.get_ramps_for_lake(lake_id)

    def get_ramp_by_id(self, ramp_id: int) -> Optional[dict]:
        return self._lake_service.get_ramp_by_id(ramp_id)

    def validate_lake_ramp_combo(self, lake_id: int, ramp_id: int) -> bool:
        return self._lake_service.validate_lake_ramp_combo(lake_id, ramp_id)
