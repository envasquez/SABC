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

    # Create excerpt (first 200 chars of content)
    excerpt = content[:200] + ("..." if len(content) > 200 else "")
    news_url = f"{WEBSITE_URL}/#news"

    # Format author signature
    formatted_author = _format_author_name(author_name)
    author_line = f"\n- {formatted_author}" if formatted_author else ""
    author_html = f"<br>- {formatted_author}" if formatted_author else ""

    text_body = f"""
Hello,

{CLUB_NAME} has posted a new update:

{title}

{excerpt}

Read the full update at: {news_url}

Thanks,
The {CLUB_NAME} Team{author_line}
"""

    html_body = f"""
<html>
<body>
<p>Hello,</p>
<p>{CLUB_NAME} has posted a new update:</p>
<h2>{title}</h2>
<p>{excerpt}</p>
<p><a href="{news_url}">Read the full update</a></p>
<p>Thanks,<br>The {CLUB_NAME} Team{author_html}</p>
</body>
</html>
"""

    return subject, text_body, html_body
