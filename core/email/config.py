import os

from core.helpers.logging import get_logger

logger = get_logger("email_service")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")  # Gmail address
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")  # App-specific password
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@saustinbc.com")
CLUB_NAME = "South Austin Bass Club"
WEBSITE_URL = os.environ.get("WEBSITE_URL", "http://localhost:8000")

# Optional group/mailing-list address for member discussion. When set, news
# notification emails carry a Reply-To pointing here, so a member's reply (or
# reply-all) reaches the list and is re-broadcast to everyone on it. Point this
# at a mailing list (e.g. a Google Group) whose membership tracks the roster.
# Leave unset to keep the current behavior (replies go only to FROM_EMAIL).
NEWS_REPLY_TO = os.environ.get("NEWS_REPLY_TO")

RESET_RATE_LIMIT = int(os.environ.get("RESET_RATE_LIMIT", "3"))
RESET_RATE_WINDOW = int(os.environ.get("RESET_RATE_WINDOW", "3600"))

TOKEN_EXPIRY_MINUTES = int(os.environ.get("TOKEN_EXPIRY_MINUTES", "30"))

# Testing: Override email recipients for development/testing
# When set, ALL emails (news, password reset, etc) will ONLY go to this address
# Example: TEST_EMAIL_OVERRIDE=your.email@gmail.com
TEST_EMAIL_OVERRIDE = os.environ.get("TEST_EMAIL_OVERRIDE")
