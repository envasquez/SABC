from datetime import datetime
from typing import Optional

from core.services.base import BaseService


class AnglerService(BaseService):
    def get_all_members(self) -> list[dict]:
        return self.fetch_all("SELECT * FROM anglers WHERE member = TRUE ORDER BY name")

    def get_all_anglers(self) -> list[dict]:
        return self.fetch_all("SELECT * FROM anglers ORDER BY name")

    def get_admin_anglers_list(self) -> list[dict]:
        current_year = datetime.now().year
        return self.fetch_all(
            {"year": current_year},
        )

    def get_angler_stats(self, angler_id: int, year: Optional[int] = None) -> dict:
        params = {"angler_id": angler_id}
        if year:
            params["year"] = str(year)

        return self.fetch_one(
            params,
        ) or {
            "tournaments_fished": 0,
            "total_fish": 0,
            "total_weight": 0,
            "biggest_bass": 0,
            "avg_weight": 0,
        }
