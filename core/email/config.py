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

RESET_RATE_LIMIT = int(os.environ.get("RESET_RATE_LIMIT", "3"))
RESET_RATE_WINDOW = int(os.environ.get("RESET_RATE_WINDOW", "3600"))

TOKEN_EXPIRY_MINUTES = int(os.environ.get("TOKEN_EXPIRY_MINUTES", "30"))
