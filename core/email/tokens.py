import secrets
import sys
from datetime import timedelta
from typing import Optional

from core.helpers.timezone import now_utc

from .config import RESET_RATE_LIMIT, RESET_RATE_WINDOW, TOKEN_EXPIRY_MINUTES, logger
from .token_queries import (
    check_rate_limit,
    delete_expired_tokens,
    fetch_token_data,
    insert_token,
    mark_token_used,
)


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def create_password_reset_token(user_id: int, email: str) -> Optional[str]:
    try:
        since = now_utc() - timedelta(seconds=RESET_RATE_WINDOW)
        recent_count = check_rate_limit(user_id, since)
        if recent_count and recent_count >= RESET_RATE_LIMIT:
            logger.warning(f"Rate limit exceeded for user {user_id} ({email})")
            return None

        token = generate_reset_token()
        expires_at = now_utc() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
        if insert_token(user_id, token, expires_at):
            logger.info(f"Created password reset token for user {user_id} ({email})")
            return token
        return None
    except Exception as e:
        logger.error(f"Failed to create reset token for user {user_id}: {e}")
        return None


def verify_reset_token(token: str) -> Optional[dict]:
    try:
        result = fetch_token_data(token)
        if not result:
            logger.warning(f"Invalid password reset token: {token[:10]}...")
            return None

        user_id, expires_at, used, email, name = result
        if used:
            logger.warning(f"Already used password reset token for user {user_id}")
            return None

        if now_utc() > expires_at:
            logger.warning(f"Expired password reset token for user {user_id}")
            return None
        return {"user_id": user_id, "email": email, "name": name, "expires_at": expires_at}
    except Exception as e:
        # Use try-except to prevent logging failures from breaking the app
        try:
            logger.error(f"Error verifying reset token: {e}")
        except Exception:
            # Fallback to print if logging fails (e.g., file handler issues)
            print(f"Error verifying reset token: {e}", file=sys.stderr)
        return None


def use_reset_token(token: str) -> bool:
    try:
        rowcount = mark_token_used(token)

        if rowcount > 0:
            logger.info(f"Marked reset token as used: {token[:10]}...")
            return True
        else:
            logger.warning(f"Failed to mark token as used: {token[:10]}...")
            return False
    except Exception as e:
        logger.error(f"Error marking token as used: {e}")
        return False


def cleanup_expired_tokens() -> int:
    try:
        deleted_count = delete_expired_tokens()
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired/used password reset tokens")
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {e}")
        return 0
