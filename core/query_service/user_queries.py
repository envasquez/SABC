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
}


class UserQueries(QueryServiceBase):
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.fetch_one(
            "SELECT * FROM anglers WHERE LOWER(email) = LOWER(:email)", {"email": email}
        )

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.fetch_one("SELECT * FROM anglers WHERE id = :id", {"id": user_id})

    def update_user(self, user_id: int, updates: dict) -> None:
        # Validate all column names against whitelist to prevent SQL injection
        invalid_columns = set(updates.keys()) - ALLOWED_UPDATE_COLUMNS
        if invalid_columns:
            raise ValueError(f"Invalid column names: {', '.join(invalid_columns)}")

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
        self.execute("DELETE FROM anglers WHERE id = :id", {"id": user_id})
