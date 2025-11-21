"""Database queries for password reset tokens."""

from datetime import datetime
from typing import Optional

from core.db_schema import Angler, PasswordResetToken, get_session
from core.helpers.timezone import now_utc

from .config import logger


def check_rate_limit(user_id: int, since: datetime) -> Optional[int]:
    try:
        with get_session() as session:
            count = (
                session.query(PasswordResetToken)
                .filter(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.created_at > since,
                )
                .count()
            )
            return count
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return None


def insert_token(user_id: int, token: str, expires_at: datetime) -> bool:
    try:
        with get_session() as session:
            reset_token = PasswordResetToken(
                user_id=user_id,
                token=token,
                expires_at=expires_at,
                created_at=now_utc(),
            )
            session.add(reset_token)
            return True
    except Exception as e:
        logger.error(f"Error inserting token: {e}")
        return False


def fetch_token_data(token: str) -> Optional[tuple]:
    try:
        with get_session() as session:
            result = (
                session.query(
                    PasswordResetToken.user_id,
                    PasswordResetToken.expires_at,
                    PasswordResetToken.used,
                    Angler.email,
                    Angler.name,
                )
                .join(Angler, PasswordResetToken.user_id == Angler.id)
                .filter(PasswordResetToken.token == token)
                .first()
            )
            return result  # type: ignore[return-value]
    except Exception as e:
        logger.error(f"Error fetching token data: {e}")
        return None


def mark_token_used(token: str) -> int:
    try:
        with get_session() as session:
            from sqlalchemy import false

            rowcount = (
                session.query(PasswordResetToken)
                .filter(
                    PasswordResetToken.token == token,
                    PasswordResetToken.used.is_(false()),
                )
                .update({"used": True, "used_at": now_utc()})
            )
            return rowcount
    except Exception as e:
        logger.error(f"Error marking token as used: {e}")
        return 0


def delete_expired_tokens() -> int:
    try:
        with get_session() as session:
            from sqlalchemy import or_, true

            rowcount = (
                session.query(PasswordResetToken)
                .filter(
                    or_(
                        PasswordResetToken.expires_at < now_utc(),
                        PasswordResetToken.used.is_(true()),
                    )
                )
                .delete()
            )
            return rowcount
    except Exception as e:
        logger.error(f"Error deleting expired tokens: {e}")
        return 0
