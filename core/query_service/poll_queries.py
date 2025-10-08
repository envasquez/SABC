"""Poll-related database queries with full type safety."""

from typing import Any, Dict, List, Optional

from core.query_service.base import QueryServiceBase


class PollQueries(QueryServiceBase):
    """Query service for poll database operations."""

    def get_poll_by_id(self, poll_id: int) -> Optional[Dict[str, Any]]:
        """
        Get poll by ID with all options included.

        Args:
            poll_id: Poll ID to fetch

        Returns:
            Poll dictionary with options list, or None if not found
        """
        poll = self.fetch_one("SELECT * FROM polls WHERE id = :id", {"id": poll_id})
        if poll:
            poll["options"] = self.fetch_all(
                "SELECT * FROM poll_options WHERE poll_id = :poll_id ORDER BY id",
                {"poll_id": poll_id},
            )
        return poll

    def get_active_polls(self) -> List[Dict[str, Any]]:
        """
        Get all currently active polls.

        Returns:
            List of active poll dictionaries ordered by closing time
        """
        return self.fetch_all(
            """
            SELECT * FROM polls
            WHERE starts_at <= CURRENT_TIMESTAMP
            AND closes_at >= CURRENT_TIMESTAMP
            ORDER BY closes_at
        """
        )

    def get_user_vote(self, poll_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's vote for a specific poll.

        Args:
            poll_id: Poll ID to check
            user_id: User ID to check

        Returns:
            Vote dictionary if user has voted, None otherwise
        """
        return self.fetch_one(
            "SELECT * FROM poll_votes WHERE poll_id = :poll_id AND angler_id = :user_id",
            {"poll_id": poll_id, "user_id": user_id},
        )

    def get_poll_options_with_votes(
        self, poll_id: int, include_details: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get poll options with vote counts and optionally voter names.

        Args:
            poll_id: Poll ID to fetch options for
            include_details: If True, include list of voter names for each option

        Returns:
            List of option dictionaries with vote_count and optionally voters list
        """
        options = self.fetch_all(
            """
            SELECT po.*, COUNT(pv.id) as vote_count
            FROM poll_options po
            LEFT JOIN poll_votes pv ON po.id = pv.option_id
            WHERE po.poll_id = :poll_id
            GROUP BY po.id
            ORDER BY vote_count DESC, po.id
        """,
            {"poll_id": poll_id},
        )
        if include_details:
            for option in options:
                voters = self.fetch_all(
                    """
                    SELECT a.name FROM poll_votes pv
                    JOIN anglers a ON pv.angler_id = a.id
                    WHERE pv.option_id = :option_id
                    ORDER BY a.name
                """,
                    {"option_id": option["id"]},
                )
                option["voters"] = [v["name"] for v in voters]
        return options
