from datetime import datetime

from core.query_service.base import QueryServiceBase


class MemberQueries(QueryServiceBase):
    def get_all_members(self) -> list[dict]:
        return self.fetch_all("SELECT * FROM anglers WHERE member = TRUE ORDER BY name")

    def get_all_anglers(self) -> list[dict]:
        return self.fetch_all("SELECT * FROM anglers ORDER BY name")

    def get_admin_anglers_list(self) -> list[dict]:
        current_year = datetime.now().year
        return self.fetch_all(
            """
            SELECT a.id, a.name, a.email, a.phone, a.member, a.is_admin,
                   STRING_AGG(op.position, ', ' ORDER BY op.position) as officer_positions
            FROM anglers a
            LEFT JOIN officer_positions op ON a.id = op.angler_id AND op.year = :year
            GROUP BY a.id, a.name, a.email, a.phone, a.member, a.is_admin
            ORDER BY a.is_admin DESC, a.member DESC, a.name
            """,
            {"year": current_year},
        )
