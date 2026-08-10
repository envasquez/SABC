import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from .config import (
    FROM_EMAIL,
    NEWS_REPLY_TO,
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
    generate_reply_email_content,
    generate_reset_email_content,
)


def _safe_header(value: str) -> str:
    """Strip CR/LF from a value before it is placed in an email header.

    Header injection (e.g. embedding ``\\r\\nBcc: attacker@example.com``) lets
    an attacker turn a public form into an open relay or rewrite envelope
    recipients. Headers cannot legitimately contain CR or LF, so strip them.
    Use only for header values; message bodies may legitimately contain CRLF.
    """
    return value.replace("\r", "").replace("\n", "")


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
        msg["To"] = _safe_header(recipient)
        msg["Subject"] = _safe_header(subject)

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
        subject, text_body, html_body = generate_news_email_content(
            title, content, author_name, reply_to=NEWS_REPLY_TO
        )

        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["Subject"] = _safe_header(subject)
        # When a discussion list is configured, point replies (and reply-all)
        # at it so members can discuss the update over email.
        if NEWS_REPLY_TO:
            msg["Reply-To"] = _safe_header(NEWS_REPLY_TO)

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)

            # Send to all members (BCC so recipients don't see the roster)
            msg["To"] = FROM_EMAIL  # Send to self
            msg["Bcc"] = ", ".join(_safe_header(e) for e in emails)
            server.send_message(msg)

        logger.info(f"News notification sent to {len(emails)} members: {title}")
        return True

    except Exception as e:
        logger.error(f"Failed to send news notification '{title}': {e}")
        return False


def send_reply_notification(
    email: str,
    recipient_name: str,
    replier_name: str,
    poll_title: str,
    reply_body: str,
    poll_url: str,
) -> bool:
    """Notify a member that someone replied to their poll comment.

    Args:
        email: Recipient's email address
        recipient_name: Recipient's display name
        replier_name: Name of the member who replied
        poll_title: Title of the poll the discussion belongs to
        reply_body: Full text of the reply
        poll_url: Link back to the poll discussion

    Returns:
        True if the email was sent, False otherwise.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured - cannot send email")
        return False

    recipient = TEST_EMAIL_OVERRIDE if TEST_EMAIL_OVERRIDE else email
    if TEST_EMAIL_OVERRIDE:
        logger.info(f"TEST MODE: Redirecting reply notification from {email} to {recipient}")

    try:
        subject, text_body, html_body = generate_reply_email_content(
            recipient_name, replier_name, poll_title, reply_body, poll_url
        )

        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["To"] = _safe_header(recipient)
        msg["Subject"] = _safe_header(subject)

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Reply notification sent to {recipient}")
        return True

    except Exception as e:
        logger.error(f"Failed to send reply notification to {recipient}: {e}")
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
        msg["To"] = ", ".join(_safe_header(e) for e in admin_emails)
        msg["Reply-To"] = _safe_header(sender_email)
        msg["Subject"] = _safe_header(subject)

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
