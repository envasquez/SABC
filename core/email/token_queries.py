"""Database queries for password reset tokens."""

import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from core.db_schema import Angler, PasswordResetToken, get_session
from core.helpers.timezone import now_utc

from .config import logger


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a reset token.

    Tokens are stored and queried as hashes so that a database disclosure
    cannot be used to forge a valid reset link. The plaintext token is only
    ever sent to the user via email.
    """
    return hashlib.sha256(token.encode()).hexdigest()


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
        token_hash = _hash_token(token)
        with get_session() as session:
            reset_token = PasswordResetToken(
                user_id=user_id,
                token=token_hash,
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
        token_hash = _hash_token(token)
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
                .filter(PasswordResetToken.token == token_hash)
                .first()
            )
            return result  # type: ignore[return-value]
    except Exception as e:
        logger.error(f"Error fetching token data: {e}")
        return None


def mark_token_used_in_session(session: Session, token: str) -> int:
    """Mark token used within an existing session. Returns rowcount.

    Use this when the caller pairs token consumption with another write
    (e.g. password update) in a single transaction so that either both
    land or neither does, preventing a token from outliving its password
    change if a downstream step fails.
    """
    from sqlalchemy import false

    token_hash = _hash_token(token)
    return (
        session.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == token_hash,
            PasswordResetToken.used.is_(false()),
        )
        .update({"used": True, "used_at": now_utc()})
    )


def mark_token_used(token: str) -> int:
    try:
        with get_session() as session:
            return mark_token_used_in_session(session, token)
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
