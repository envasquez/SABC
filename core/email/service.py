import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from .config import (
    FROM_EMAIL,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_USERNAME,
    TEST_EMAIL_OVERRIDE,
    logger,
)
from .templates import (
    generate_contact_email_content,
    generate_news_email_content,
    generate_reset_email_content,
)


def send_password_reset_email(email: str, name: str, token: str) -> bool:
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured - cannot send email")
        return False

    # Override recipient for testing
    recipient = TEST_EMAIL_OVERRIDE if TEST_EMAIL_OVERRIDE else email
    if TEST_EMAIL_OVERRIDE:
        logger.info(f"TEST MODE: Redirecting password reset email from {email} to {recipient}")

    try:
        subject, text_body, html_body = generate_reset_email_content(name, token)

        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Password reset email sent to {recipient}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {recipient}: {e}")
        return False


def send_news_notification(
    emails: List[str], title: str, content: str, author_name: str | None = None
) -> bool:
    """Send news notification to multiple members.

    Args:
        emails: List of email addresses to send to
        title: News post title
        content: News post content
        author_name: Optional name of the author who posted the news

    Returns:
        True if emails sent successfully, False otherwise
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured - cannot send email")
        return False

    if not emails:
        logger.info("No email addresses provided - skipping news notification")
        return True

    # Override recipients for testing
    if TEST_EMAIL_OVERRIDE:
        original_count = len(emails)
        emails = [TEST_EMAIL_OVERRIDE]
        logger.info(
            f"TEST MODE: Redirecting news notification from {original_count} members to {TEST_EMAIL_OVERRIDE}"
        )

    try:
        subject, text_body, html_body = generate_news_email_content(title, content, author_name)

        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)

            # Send to all members (BCC so recipients don't see the roster)
            msg["To"] = FROM_EMAIL  # Send to self
            msg["Bcc"] = ", ".join(emails)
            server.send_message(msg)

        logger.info(f"News notification sent to {len(emails)} members: {title}")
        return True

    except Exception as e:
        logger.error(f"Failed to send news notification '{title}': {e}")
        return False


def send_contact_email(
    admin_emails: List[str],
    sender_name: str,
    sender_email: str,
    subject_line: str,
    message: str,
) -> bool:
    """Send a contact form submission to all admin users.

    Args:
        admin_emails: List of admin email addresses
        sender_name: Name of the person submitting the form
        sender_email: Email of the person submitting the form
        subject_line: Subject provided by the sender
        message: Message body from the contact form

    Returns:
        True if email sent successfully, False otherwise
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured - cannot send contact email")
        return False

    if not admin_emails:
        logger.info("No admin email addresses provided - skipping contact email")
        return False

    # Override recipients for testing
    if TEST_EMAIL_OVERRIDE:
        original_count = len(admin_emails)
        admin_emails = [TEST_EMAIL_OVERRIDE]
        logger.info(
            f"TEST MODE: Redirecting contact email from {original_count} admins to {TEST_EMAIL_OVERRIDE}"
        )

    try:
        subject, text_body, html_body = generate_contact_email_content(
            sender_name, sender_email, subject_line, message
        )

        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["To"] = ", ".join(admin_emails)
        msg["Reply-To"] = sender_email
        msg["Subject"] = subject

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(
            f"Contact email sent to {len(admin_emails)} admins from {sender_email}: {subject_line}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send contact email from {sender_email}: {e}")
        return False
