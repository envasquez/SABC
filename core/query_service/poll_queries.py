from typing import Optional

from core.query_service.base import QueryServiceBase


class PollQueries(QueryServiceBase):
    def get_poll_by_id(self, poll_id: int) -> Optional[dict]:
        poll = self.fetch_one("SELECT * FROM polls WHERE id = :id", {"id": poll_id})
        if poll:
            poll["options"] = self.fetch_all(
                "SELECT * FROM poll_options WHERE poll_id = :poll_id ORDER BY id",
                {"poll_id": poll_id},
            )
        return poll

    def get_active_polls(self) -> list[dict]:
        return self.fetch_all("""
            SELECT * FROM polls
            WHERE starts_at <= CURRENT_TIMESTAMP
            AND closes_at >= CURRENT_TIMESTAMP
            ORDER BY closes_at
        """)

    def get_user_vote(self, poll_id: int, user_id: int) -> Optional[dict]:
        return self.fetch_one(
            "SELECT * FROM poll_votes WHERE poll_id = :poll_id AND angler_id = :user_id",
            {"poll_id": poll_id, "user_id": user_id},
        )

    def get_poll_options_with_votes(
        self, poll_id: int, include_details: bool = False
    ) -> list[dict]:
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
