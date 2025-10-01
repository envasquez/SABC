"""Database queries for password reset tokens."""

from datetime import datetime
from typing import Optional

from sqlalchemy import text

from core.db_schema import engine

from .config import logger


def check_rate_limit(user_id: int, since: datetime) -> Optional[int]:
    """Check how many tokens were created for user since given time."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT COUNT(*) FROM password_reset_tokens
                       WHERE user_id = :user_id AND created_at > :since"""),
                {"user_id": user_id, "since": since},
            ).scalar()
            return result
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return None


def insert_token(user_id: int, token: str, expires_at: datetime) -> bool:
    """Insert new password reset token into database."""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
                       VALUES (:user_id, :token, :expires_at, NOW())"""),
                {"user_id": user_id, "token": token, "expires_at": expires_at},
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error inserting token: {e}")
        return False


def fetch_token_data(token: str) -> Optional[tuple]:
    """Fetch token data from database."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT prt.user_id, prt.expires_at, prt.used, a.email, a.name
                       FROM password_reset_tokens prt
                       JOIN anglers a ON prt.user_id = a.id
                       WHERE prt.token = :token"""),
                {"token": token},
            ).fetchone()
            return result
    except Exception as e:
        logger.error(f"Error fetching token data: {e}")
        return None


def mark_token_used(token: str) -> int:
    """Mark token as used in database."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""UPDATE password_reset_tokens
                       SET used = TRUE, used_at = NOW()
                       WHERE token = :token AND used = 0"""),
                {"token": token},
            )
            conn.commit()
            return result.rowcount
    except Exception as e:
        logger.error(f"Error marking token as used: {e}")
        return 0


def delete_expired_tokens() -> int:
    """Delete expired and used tokens from database."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""DELETE FROM password_reset_tokens
                       WHERE expires_at < NOW() OR used = 1""")
            )
            conn.commit()
            return result.rowcount
    except Exception as e:
        logger.error(f"Error deleting expired tokens: {e}")
        return 0
