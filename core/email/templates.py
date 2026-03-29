from .config import CLUB_NAME, WEBSITE_URL


def generate_reset_email_content(name: str, token: str) -> tuple[str, str, str]:
    subject = f"{CLUB_NAME} - Reset Your Password"
    reset_url = f"{WEBSITE_URL}/reset-password?token={token}"

    text_body = f"""
Hello {name},

You recently requested to reset your password for your {CLUB_NAME} account.

To reset your password, click the link below:
{reset_url}

This link will expire in 24 hours.

If you did not request a password reset, please ignore this email.

Thanks,
The {CLUB_NAME} Team
"""

    html_body = f"""
<html>
<body>
<p>Hello {name},</p>
<p>You recently requested to reset your password for your {CLUB_NAME} account.</p>
<p>To reset your password, click the link below:</p>
<p><a href="{reset_url}">Reset Your Password</a></p>
<p>This link will expire in 24 hours.</p>
<p>If you did not request a password reset, please ignore this email.</p>
<p>Thanks,<br>The {CLUB_NAME} Team</p>
</body>
</html>
"""

    return subject, text_body, html_body


def _format_author_name(author_name: str | None) -> str:
    """Format author name as first initial + last name (e.g., 'J. Smith')."""
    if not author_name:
        return ""
    parts = author_name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {parts[-1]}"
    return author_name


def generate_news_email_content(
    title: str, content: str, author_name: str | None = None
) -> tuple[str, str, str]:
    """Generate email content for news notifications.

    Args:
        title: News post title
        content: Full news content
        author_name: Optional name of the author who posted the news

    Returns:
        Tuple of (subject, text_body, html_body)
    """
    subject = f"{CLUB_NAME} - {title}"

    news_url = f"{WEBSITE_URL}/#news"

    # Format author signature
    formatted_author = _format_author_name(author_name)
    author_line = f"\n- {formatted_author}" if formatted_author else ""
    author_html = f"<br>- {formatted_author}" if formatted_author else ""

    # Convert content to HTML paragraphs (preserve line breaks)
    html_content = "".join(f"<p>{line}</p>" for line in content.split("\n") if line.strip())

    text_body = f"""
Hello,

{CLUB_NAME} has posted a new update:

{title}

{content}

View this post on our website: {news_url}

Thanks,
The {CLUB_NAME} Team{author_line}
"""

    html_body = f"""
<html>
<body>
<p>Hello,</p>
<p>{CLUB_NAME} has posted a new update:</p>
<h2>{title}</h2>
{html_content}
<p><a href="{news_url}">View this post on our website</a></p>
<p>Thanks,<br>The {CLUB_NAME} Team{author_html}</p>
</body>
</html>
"""

    return subject, text_body, html_body


def generate_contact_email_content(
    sender_name: str, sender_email: str, subject_line: str, message: str
) -> tuple[str, str, str]:
    """Generate email content for contact form submissions.

    Args:
        sender_name: Name of the person submitting the form
        sender_email: Email of the person submitting the form
        subject_line: Subject provided by the sender
        message: Message body from the contact form

    Returns:
        Tuple of (subject, text_body, html_body)
    """
    subject = f"{CLUB_NAME} - Contact: {subject_line}"

    text_body = f"""
New contact form submission from {WEBSITE_URL}:

From: {sender_name} ({sender_email})
Subject: {subject_line}

{message}

---
This message was sent via the {CLUB_NAME} website contact form.
You can reply directly to {sender_email}.
"""

    # Convert message line breaks to HTML
    html_message = "".join(
        f"<p>{line}</p>" if line.strip() else "<br>" for line in message.split("\n")
    )

    html_body = f"""
<html>
<body>
<p>New contact form submission from <a href="{WEBSITE_URL}">{CLUB_NAME}</a>:</p>
<table style="border-collapse: collapse; margin: 16px 0;">
<tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">From:</td><td>{sender_name} ({sender_email})</td></tr>
<tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">Subject:</td><td>{subject_line}</td></tr>
</table>
<div style="padding: 12px; background-color: #f5f5f5; border-left: 4px solid #0d6efd; margin: 16px 0;">
{html_message}
</div>
<hr>
<p style="color: #6c757d; font-size: 0.875em;">
This message was sent via the {CLUB_NAME} website contact form.
You can reply directly to <a href="mailto:{sender_email}">{sender_email}</a>.
</p>
</body>
</html>
"""

    return subject, text_body, html_body
