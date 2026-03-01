"""Member-related database queries with full type safety."""

from typing import Any, Dict, List

from core.helpers.timezone import now_local
from core.query_service.base import QueryServiceBase


class MemberQueries(QueryServiceBase):
    """Query service for member/angler database operations."""

    def get_all_members(self) -> List[Dict[str, Any]]:
        """
        Get all club members.

        Returns:
            List of member dictionaries ordered by name
        """
        return self.fetch_all("SELECT * FROM anglers WHERE member = TRUE ORDER BY name")

    def get_all_anglers(self) -> List[Dict[str, Any]]:
        """
        Get all anglers (members and non-members).

        Returns:
            List of angler dictionaries ordered by name
        """
        return self.fetch_all("SELECT * FROM anglers ORDER BY name")

    def get_admin_anglers_list(self) -> List[Dict[str, Any]]:
        """
        Get all anglers with officer positions for admin interface.

        Returns:
            List of angler dictionaries with officer_positions aggregated
        """
        current_year = now_local().year
        return self.fetch_all(
            """
            SELECT a.id, a.name, a.email, a.phone, a.member, a.is_admin,
                   a.dues_paid_through,
                   STRING_AGG(op.position, ', ' ORDER BY op.position) as officer_positions
            FROM anglers a
            LEFT JOIN officer_positions op ON a.id = op.angler_id AND op.year = :year
            GROUP BY a.id, a.name, a.email, a.phone, a.member, a.is_admin, a.dues_paid_through
            ORDER BY a.is_admin DESC, a.member DESC, a.name
            """,
            {"year": current_year},
        )
