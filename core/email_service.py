"""
Simple email service for password reset functionality.
Designed for non-tech-savvy users with clear, simple emails.
"""

import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy import text

from core.db_schema import engine
from core.helpers.logging_config import get_logger

logger = get_logger("email_service")

# Email configuration - using Gmail SMTP (free)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")  # Gmail address
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")  # App-specific password
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@saustinbc.com")
CLUB_NAME = "South Austin Bass Club"
WEBSITE_URL = os.environ.get("WEBSITE_URL", "http://localhost:8000")

# Rate limiting: max 3 reset requests per hour per email
RESET_RATE_LIMIT = 3
RESET_RATE_WINDOW = 3600  # 1 hour in seconds

# Token expiration: 30 minutes (user-friendly for older folks)
TOKEN_EXPIRY_MINUTES = 30


def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def create_password_reset_token(user_id: int, email: str) -> Optional[str]:
    """
    Create a password reset token for a user.
    Returns token if successful, None if rate limited or error.
    """
    try:
        with engine.connect() as conn:
            # Check rate limiting: count recent tokens for this user
            recent_count = conn.execute(
                text("""
                    SELECT COUNT(*) FROM password_reset_tokens
                    WHERE user_id = :user_id
                    AND created_at > :since
                """),
                {
                    "user_id": user_id,
                    "since": datetime.now() - timedelta(seconds=RESET_RATE_WINDOW),
                },
            ).scalar()

            if recent_count and recent_count >= RESET_RATE_LIMIT:
                logger.warning(f"Rate limit exceeded for user {user_id} ({email})")
                return None

            # Generate token and expiry
            token = generate_reset_token()
            expires_at = datetime.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)

            # Insert token into database
            conn.execute(
                text("""
                    INSERT INTO password_reset_tokens (user_id, token, expires_at)
                    VALUES (:user_id, :token, :expires_at)
                """),
                {"user_id": user_id, "token": token, "expires_at": expires_at},
            )
            conn.commit()

            logger.info(f"Created password reset token for user {user_id} ({email})")
            return token

    except Exception as e:
        logger.error(f"Failed to create reset token for user {user_id}: {e}")
        return None


def send_password_reset_email(email: str, name: str, token: str) -> bool:
    """
    Send a simple, clear password reset email.
    Designed for non-tech-savvy users.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured - cannot send email")
        return False

    try:
        # Create the reset URL
        reset_url = f"{WEBSITE_URL}/reset-password?token={token}"

        # Create simple, clear email content
        subject = f"{CLUB_NAME} - Reset Your Password"

        # Plain text version (for older email clients)
        text_body = f"""
Hello {name},

Someone requested to reset the password for your {CLUB_NAME} account.

To reset your password, click this link or copy it into your web browser:
{reset_url}

This link will expire in {TOKEN_EXPIRY_MINUTES} minutes for your security.

If you didn't request this password reset, you can safely ignore this email.
Your password will not be changed.

Need help? Contact your club administrator.

Best regards,
{CLUB_NAME}
        """.strip()

        # HTML version (prettier for modern email clients)
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c5aa0;">{CLUB_NAME}</h2>
        <h3>Reset Your Password</h3>

        <p>Hello <strong>{name}</strong>,</p>

        <p>Someone requested to reset the password for your {CLUB_NAME} account.</p>

        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; margin: 20px 0;">
            <p><strong>To reset your password:</strong></p>
            <p><a href="{reset_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset My Password</a></p>
            <p style="font-size: 12px; color: #6c757d; margin-top: 10px;">
                Or copy this link: <br>
                <span style="word-break: break-all;">{reset_url}</span>
            </p>
        </div>

        <p><strong>Important:</strong> This link will expire in <strong>{TOKEN_EXPIRY_MINUTES} minutes</strong> for your security.</p>

        <p>If you didn't request this password reset, you can safely ignore this email. Your password will not be changed.</p>

        <p>Need help? Contact your club administrator.</p>

        <hr style="margin: 30px 0; border: 1px solid #dee2e6;">
        <p style="font-size: 12px; color: #6c757d;">
            Best regards,<br>
            {CLUB_NAME}
        </p>
    </div>
</body>
</html>
        """.strip()

        # Create email message
        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["To"] = email
        msg["Subject"] = subject

        # Attach both plain text and HTML versions
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send email via Gmail SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Password reset email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False


def verify_reset_token(token: str) -> Optional[dict]:
    """
    Verify a password reset token.
    Returns user info if valid, None if invalid/expired.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT prt.user_id, prt.expires_at, prt.used, a.email, a.name
                    FROM password_reset_tokens prt
                    JOIN anglers a ON prt.user_id = a.id
                    WHERE prt.token = :token
                """),
                {"token": token},
            ).fetchone()

            if not result:
                logger.warning(f"Invalid password reset token: {token[:10]}...")
                return None

            user_id, expires_at, used, email, name = result

            # Check if token is already used
            if used:
                logger.warning(f"Already used password reset token for user {user_id}")
                return None

            # Check if token is expired
            if datetime.now() > expires_at:
                logger.warning(f"Expired password reset token for user {user_id}")
                return None

            return {"user_id": user_id, "email": email, "name": name, "expires_at": expires_at}

    except Exception as e:
        logger.error(f"Error verifying reset token: {e}")
        return None


def use_reset_token(token: str) -> bool:
    """
    Mark a password reset token as used.
    Returns True if successful.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE password_reset_tokens
                    SET used = TRUE, used_at = CURRENT_TIMESTAMP
                    WHERE token = :token AND used = FALSE
                """),
                {"token": token},
            )
            conn.commit()

            if result.rowcount > 0:
                logger.info(f"Marked reset token as used: {token[:10]}...")
                return True
            else:
                logger.warning(f"Failed to mark token as used: {token[:10]}...")
                return False

    except Exception as e:
        logger.error(f"Error marking token as used: {e}")
        return False


def cleanup_expired_tokens() -> int:
    """
    Clean up expired password reset tokens.
    Returns number of tokens deleted.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    DELETE FROM password_reset_tokens
                    WHERE expires_at < CURRENT_TIMESTAMP OR used = TRUE
                """)
            )
            conn.commit()

            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired/used password reset tokens")

            return deleted_count

    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {e}")
        return 0
