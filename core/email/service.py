import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from .config import FROM_EMAIL, SMTP_PASSWORD, SMTP_PORT, SMTP_SERVER, SMTP_USERNAME, logger
from .templates import generate_news_email_content, generate_reset_email_content


def send_password_reset_email(email: str, name: str, token: str) -> bool:
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured - cannot send email")
        return False

    try:
        subject, text_body, html_body = generate_reset_email_content(name, token)

        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["To"] = email
        msg["Subject"] = subject

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Password reset email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False


def send_news_notification(emails: List[str], title: str, content: str) -> bool:
    """Send news notification to multiple members.

    Args:
        emails: List of email addresses to send to
        title: News post title
        content: News post content

    Returns:
        True if emails sent successfully, False otherwise
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured - cannot send email")
        return False

    if not emails:
        logger.info("No email addresses provided - skipping news notification")
        return True

    try:
        subject, text_body, html_body = generate_news_email_content(title, content)

        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)

            # Send to all members (BCC to protect privacy)
            msg["To"] = FROM_EMAIL  # Send to self
            msg["Bcc"] = ", ".join(emails)
            server.send_message(msg)

        logger.info(f"News notification sent to {len(emails)} members: {title}")
        return True

    except Exception as e:
        logger.error(f"Failed to send news notification '{title}': {e}")
        return False
