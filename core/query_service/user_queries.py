"""User-related database queries with full type safety."""

from typing import Any, Dict, Optional

from core.query_service.base import QueryServiceBase

# Whitelist of allowed columns for user updates to prevent SQL injection
ALLOWED_UPDATE_COLUMNS = {
    "name",
    "email",
    "phone",
    "password",
    "member",
    "is_admin",
    "dues_paid_through",
    "dues_banner_dismissed_at",
}


class UserQueries(QueryServiceBase):
    """Query service for user/angler database operations."""

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email address (case-insensitive).

        Args:
            email: Email address to search for

        Returns:
            User dictionary if found, None otherwise
        """
        return self.fetch_one(
            "SELECT * FROM anglers WHERE LOWER(email) = LOWER(:email)", {"email": email}
        )

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.

        Args:
            user_id: User ID to search for

        Returns:
            User dictionary if found, None otherwise
        """
        return self.fetch_one("SELECT * FROM anglers WHERE id = :id", {"id": user_id})

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> None:
        """
        Update user fields.

        Args:
            user_id: ID of user to update
            updates: Dictionary of column names and values to update

        Raises:
            ValueError: If any column names are not in ALLOWED_UPDATE_COLUMNS
        """
        # Validate all column names against whitelist to prevent SQL injection
        invalid_columns = set(updates.keys()) - ALLOWED_UPDATE_COLUMNS
        if invalid_columns:
            raise ValueError(f"Invalid column names: {', '.join(invalid_columns)}")

        set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
        params = {**updates, "id": user_id}
        # Safe: column names validated against whitelist, values parameterized
        self.execute(f"UPDATE anglers SET {set_clause} WHERE id = :id", params)  # nosec B608

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        member: bool = False,
        is_admin: bool = False,
    ) -> int:
        """
        Create a new user.

        Args:
            name: Full name of the user
            email: Email address (used for login)
            password_hash: Bcrypt hashed password
            member: Whether user is a club member
            is_admin: Whether user has admin privileges

        Returns:
            ID of newly created user
        """
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
        """
        Delete a user by ID.

        Args:
            user_id: ID of user to delete
        """
        self.execute("DELETE FROM anglers WHERE id = :id", {"id": user_id})
