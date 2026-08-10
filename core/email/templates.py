from markupsafe import escape

from .config import CLUB_NAME, TOKEN_EXPIRY_MINUTES, WEBSITE_URL


def generate_reset_email_content(name: str, token: str) -> tuple[str, str, str]:
    subject = f"{CLUB_NAME} - Reset Your Password"
    reset_url = f"{WEBSITE_URL}/reset-password?token={token}"
    expiry_text = f"{TOKEN_EXPIRY_MINUTES} minutes"

    text_body = f"""
Hello {name},

You recently requested to reset your password for your {CLUB_NAME} account.

To reset your password, click the link below:
{reset_url}

This link will expire in {expiry_text}.

If you did not request a password reset, please ignore this email.

Thanks,
The {CLUB_NAME} Team
"""

    # HTML-escape the user-controlled name to prevent injection into the
    # HTML email body.
    name_html = escape(name)

    html_body = f"""
<html>
<body>
<p>Hello {name_html},</p>
<p>You recently requested to reset your password for your {CLUB_NAME} account.</p>
<p>To reset your password, click the link below:</p>
<p><a href="{reset_url}">Reset Your Password</a></p>
<p>This link will expire in {expiry_text}.</p>
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
    title: str, content: str, author_name: str | None = None, reply_to: str | None = None
) -> tuple[str, str, str]:
    """Generate email content for news notifications.

    Args:
        title: News post title
        content: Full news content
        author_name: Optional name of the author who posted the news
        reply_to: Optional discussion-list address. When set, the email invites
            members to reply to discuss with the club (their reply goes to the
            list and is re-broadcast to everyone).

    Returns:
        Tuple of (subject, text_body, html_body)
    """
    subject = f"{CLUB_NAME} - {title}"

    news_url = f"{WEBSITE_URL}/#news"

    # Format author signature
    formatted_author = _format_author_name(author_name)
    author_line = f"\n- {formatted_author}" if formatted_author else ""

    # Invitation to reply-all discuss, only when a discussion list is configured.
    reply_invite_text = (
        "\n\n💬 Want to discuss? Just reply to this email — your reply goes to all members.\n"
        if reply_to
        else ""
    )
    reply_invite_html = (
        '<p style="padding: 10px 12px; background-color: #f5f5f5; '
        'border-left: 4px solid #0d6efd;">💬 <strong>Want to discuss?</strong> '
        "Just reply to this email — your reply goes to all members.</p>"
        if reply_to
        else ""
    )

    # Defense-in-depth: HTML-escape every user-controlled value before
    # interpolating into the HTML email body. Callers are expected to have
    # already sanitized at write time (see routes/admin/core/news.py), but
    # this guarantees a future caller (or a value persisted before the
    # sanitizer existed) cannot inject markup into recipient inboxes.
    title_html = escape(title)
    author_html_safe = f"<br>- {escape(formatted_author)}" if formatted_author else ""

    # Convert content to HTML paragraphs (preserve line breaks)
    html_content = "".join(f"<p>{escape(line)}</p>" for line in content.split("\n") if line.strip())

    text_body = f"""
Hello,

{CLUB_NAME} has posted a new update:

{title}

{content}

View this post on our website: {news_url}{reply_invite_text}

Thanks,
The {CLUB_NAME} Team{author_line}
"""

    html_body = f"""
<html>
<body>
<p>Hello,</p>
<p>{CLUB_NAME} has posted a new update:</p>
<h2>{title_html}</h2>
{html_content}
<p><a href="{news_url}">View this post on our website</a></p>
{reply_invite_html}
<p>Thanks,<br>The {CLUB_NAME} Team{author_html_safe}</p>
</body>
</html>
"""

    return subject, text_body, html_body


def generate_reply_email_content(
    recipient_name: str,
    replier_name: str,
    poll_title: str,
    reply_body: str,
    poll_url: str,
) -> tuple[str, str, str]:
    """Generate email content notifying a member that someone replied to them.

    Args:
        recipient_name: Name of the comment author being notified
        replier_name: Name of the member who posted the reply
        poll_title: Title of the poll the discussion belongs to
        reply_body: The full text of the reply (so it can be read in-inbox)
        poll_url: Link back to the poll's discussion

    Returns:
        Tuple of (subject, text_body, html_body)
    """
    subject = f"{CLUB_NAME} - {replier_name} replied to your comment"

    text_body = f"""
Hello {recipient_name},

{replier_name} replied to your comment on "{poll_title}":

{reply_body}

Read and respond on the discussion board: {poll_url}

You're receiving this because reply notifications are on. You can turn them
off any time from your profile on the {CLUB_NAME} website.

Thanks,
The {CLUB_NAME} Team
"""

    # HTML-escape every user-controlled value before interpolating into the
    # HTML body to prevent markup/script injection into recipient inboxes.
    recipient_html = escape(recipient_name)
    replier_html = escape(replier_name)
    title_html = escape(poll_title)
    body_html = "".join(f"<p>{escape(line)}</p>" for line in reply_body.split("\n") if line.strip())

    html_body = f"""
<html>
<body>
<p>Hello {recipient_html},</p>
<p><strong>{replier_html}</strong> replied to your comment on "{title_html}":</p>
<div style="padding: 12px; background-color: #f5f5f5; border-left: 4px solid #0d6efd; margin: 16px 0;">
{body_html}
</div>
<p><a href="{poll_url}">Read and respond on the discussion board</a></p>
<hr>
<p style="color: #6c757d; font-size: 0.875em;">
You're receiving this because reply notifications are on. You can turn them off
any time from your profile on the {CLUB_NAME} website.
</p>
<p>Thanks,<br>The {CLUB_NAME} Team</p>
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

    # HTML-escape all user-controlled values before interpolating into the
    # HTML email body to prevent HTML/script injection.
    sender_name_html = escape(sender_name)
    sender_email_html = escape(sender_email)
    subject_line_html = escape(subject_line)

    # Convert message line breaks to HTML (escape each line first)
    html_message = "".join(
        f"<p>{escape(line)}</p>" if line.strip() else "<br>" for line in message.split("\n")
    )

    html_body = f"""
<html>
<body>
<p>New contact form submission from <a href="{WEBSITE_URL}">{CLUB_NAME}</a>:</p>
<table style="border-collapse: collapse; margin: 16px 0;">
<tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">From:</td><td>{sender_name_html} ({sender_email_html})</td></tr>
<tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">Subject:</td><td>{subject_line_html}</td></tr>
</table>
<div style="padding: 12px; background-color: #f5f5f5; border-left: 4px solid #0d6efd; margin: 16px 0;">
{html_message}
</div>
<hr>
<p style="color: #6c757d; font-size: 0.875em;">
This message was sent via the {CLUB_NAME} website contact form.
You can reply directly to <a href="mailto:{sender_email_html}">{sender_email_html}</a>.
</p>
</body>
</html>
"""

    return subject, text_body, html_body
