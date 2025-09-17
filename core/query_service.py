"""
Consolidated query service to reduce code duplication.
Combines functionality from queries.py, common_queries.py, and other query modules.
"""

from typing import Any, Optional

from sqlalchemy import Connection, text


class QueryService:
    """Centralized database query service."""

    def __init__(self, conn: Connection):
        self.conn = conn

    def execute(self, query: str, params: Optional[dict] = None) -> Any:
        """Execute a raw query with parameters."""
        return self.conn.execute(text(query), params or {})

    def fetch_all(self, query: str, params: Optional[dict] = None) -> list[dict]:
        """Execute query and return all results as list of dicts."""
        result = self.execute(query, params)
        return [dict(row._mapping) for row in result]

    def fetch_one(self, query: str, params: Optional[dict] = None) -> Optional[dict]:
        """Execute query and return first result as dict or None."""
        results = self.fetch_all(query, params)
        return results[0] if results else None

    def fetch_value(self, query: str, params: Optional[dict] = None) -> Any:
        """Execute query and return single value from first row."""
        result = self.fetch_one(query, params)
        if result:
            return next(iter(result.values()))
        return None

    # User/Auth queries
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email address."""
        return self.fetch_one(
            "SELECT * FROM anglers WHERE LOWER(email) = LOWER(:email)", {"email": email}
        )

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Get user by ID."""
        return self.fetch_one("SELECT * FROM anglers WHERE id = :id", {"id": user_id})

    # Lake/Ramp queries
    def get_lakes_list(self) -> list[dict]:
        """Get all lakes ordered by display_name."""
        return self.fetch_all("SELECT * FROM lakes ORDER BY display_name")

    def get_lake_by_id(self, lake_id: int) -> Optional[dict]:
        """Get lake by ID."""
        return self.fetch_one("SELECT * FROM lakes WHERE id = :id", {"id": lake_id})

    def get_ramps_for_lake(self, lake_id: int) -> list[dict]:
        """Get all ramps for a specific lake."""
        return self.fetch_all(
            "SELECT * FROM ramps WHERE lake_id = :lake_id ORDER BY name", {"lake_id": lake_id}
        )

    def get_ramp_by_id(self, ramp_id: int) -> Optional[dict]:
        """Get ramp by ID."""
        return self.fetch_one("SELECT * FROM ramps WHERE id = :id", {"id": ramp_id})

    def validate_lake_ramp_combo(self, lake_id: int, ramp_id: int) -> bool:
        """Validate that a ramp belongs to a lake."""
        result = self.fetch_value(
            "SELECT COUNT(*) FROM ramps WHERE id = :ramp_id AND lake_id = :lake_id",
            {"ramp_id": ramp_id, "lake_id": lake_id},
        )
        return result > 0

    # Poll queries
    def get_poll_by_id(self, poll_id: int) -> Optional[dict]:
        """Get poll with options."""
        poll = self.fetch_one("SELECT * FROM polls WHERE id = :id", {"id": poll_id})
        if poll:
            poll["options"] = self.fetch_all(
                "SELECT * FROM poll_options WHERE poll_id = :poll_id ORDER BY id",
                {"poll_id": poll_id},
            )
        return poll

    def get_active_polls(self) -> list[dict]:
        """Get all currently active polls."""
        return self.fetch_all("""
            SELECT * FROM polls
            WHERE starts_at <= datetime('now')
            AND closes_at >= datetime('now')
            ORDER BY closes_at
        """)

    def get_user_vote(self, poll_id: int, user_id: int) -> Optional[dict]:
        """Check if user has voted in a poll."""
        return self.fetch_one(
            "SELECT * FROM poll_votes WHERE poll_id = :poll_id AND angler_id = :user_id",
            {"poll_id": poll_id, "user_id": user_id},
        )

    # Tournament queries
    def get_tournament_by_id(self, tournament_id: int) -> Optional[dict]:
        """Get tournament details."""
        return self.fetch_one(
            """
            SELECT t.*, e.date, e.name
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            WHERE t.id = :id
        """,
            {"id": tournament_id},
        )

    def get_tournament_results(self, tournament_id: int) -> list[dict]:
        """Get results for a tournament."""
        return self.fetch_all(
            """
            SELECT r.*, a.name as angler_name
            FROM results r
            JOIN anglers a ON r.angler_id = a.id
            WHERE r.tournament_id = :tournament_id AND a.name != 'Admin User'
            ORDER BY r.total_weight DESC
        """,
            {"tournament_id": tournament_id},
        )

    def get_team_results(self, tournament_id: int) -> list[dict]:
        """Get team results for a tournament."""
        return self.fetch_all(
            """
            SELECT tr.*,
                   a1.name as angler1_name,
                   a2.name as angler2_name
            FROM team_results tr
            JOIN anglers a1 ON tr.angler1_id = a1.id
            JOIN anglers a2 ON tr.angler2_id = a2.id
            WHERE tr.tournament_id = :tournament_id
            AND a1.name != 'Admin User' AND a2.name != 'Admin User'
            ORDER BY tr.total_weight DESC
        """,
            {"tournament_id": tournament_id},
        )

    # Event queries
    def get_upcoming_events(self) -> list[dict]:
        """Get upcoming events."""
        return self.fetch_all("""
            SELECT e.*,
                   p.id as poll_id,
                   p.starts_at,
                   p.closes_at,
                   t.id as tournament_id,
                   t.complete as tournament_complete
            FROM events e
            LEFT JOIN polls p ON e.id = p.event_id
            LEFT JOIN tournaments t ON e.id = t.event_id
            WHERE e.date >= date('now')
            ORDER BY e.date
        """)

    def get_past_events(self) -> list[dict]:
        """Get past events with tournament info."""
        return self.fetch_all("""
            SELECT e.*,
                   t.id as tournament_id,
                   t.complete,
                   t.lake_name,
                   t.ramp_name
            FROM events e
            LEFT JOIN tournaments t ON e.id = t.event_id
            WHERE e.date < date('now')
            ORDER BY e.date DESC
        """)

    # Member queries
    def get_all_members(self) -> list[dict]:
        """Get all members (not guests)."""
        return self.fetch_all("SELECT * FROM anglers WHERE member = TRUE ORDER BY name")

    def get_all_anglers(self) -> list[dict]:
        """Get all anglers including guests."""
        return self.fetch_all("SELECT * FROM anglers ORDER BY name")

    # Stats queries
    def get_angler_stats(self, angler_id: int, year: Optional[int] = None) -> dict:
        """Get statistics for an angler."""
        year_filter = "AND STRFTIME('%Y', e.date) = :year" if year else ""
        params = {"angler_id": angler_id}
        if year:
            params["year"] = str(year)

        return self.fetch_one(
            f"""
            SELECT
                COUNT(DISTINCT r.tournament_id) as tournaments_fished,
                SUM(r.num_fish) as total_fish,
                SUM(r.total_weight) as total_weight,
                MAX(r.big_bass_weight) as biggest_bass,
                AVG(r.total_weight) as avg_weight
            FROM results r
            JOIN tournaments t ON r.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE r.angler_id = :angler_id
            {year_filter}
        """,
            params,
        ) or {
            "tournaments_fished": 0,
            "total_fish": 0,
            "total_weight": 0,
            "biggest_bass": 0,
            "avg_weight": 0,
        }

    # Admin update queries
    def update_user(self, user_id: int, updates: dict) -> None:
        """Update user fields."""
        set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
        params = {**updates, "id": user_id}
        self.execute(f"UPDATE anglers SET {set_clause} WHERE id = :id", params)

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        member: bool = False,
        is_admin: bool = False,
    ) -> int:
        """Create a new user and return their ID."""
        result = self.execute(
            """
            INSERT INTO anglers (name, email, password, member, is_admin)
            VALUES (:name, :email, :password, :member, :is_admin)
            RETURNING id
        """,
            {
                "name": name,
                "email": email,
                "password": password_hash,
                "member": member,
                "is_admin": is_admin,
            },
        )
        return result.scalar()

    def delete_user(self, user_id: int) -> None:
        """Delete a user (with cascade handling)."""
        self.execute("DELETE FROM anglers WHERE id = :id", {"id": user_id})

    def get_poll_options_with_votes(
        self, poll_id: int, include_details: bool = False
    ) -> list[dict]:
        """Get poll options with vote counts."""
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
            # Add voter names for admin view
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
