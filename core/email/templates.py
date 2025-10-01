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
