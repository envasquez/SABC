"""
Staging-specific Django settings for SABC project.

This settings file is specifically configured for the staging environment
and inherits from base settings with staging-specific overrides.
"""

import os

from ..settings import *  # noqa: F403, F401

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "staging-secret-key-change-me-in-production")

# Allowed hosts for staging
ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "staging.yourdomain.com,localhost,127.0.0.1"
).split(",")

# Database configuration for staging
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "sabc_staging"),
        "USER": os.environ.get("POSTGRES_USER", "sabc_staging_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "staging_password_change_me"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# Redis configuration for staging
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")

# Cache configuration using Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "TIMEOUT": int(os.environ.get("CACHE_TIMEOUT", "300")),
    }
}

# Static files configuration for staging
STATIC_ROOT = os.environ.get(
    "STATIC_ROOT", "/home/sabc-staging/app/SABC_II/SABC/sabc/staticfiles"
)
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", "/home/sabc-staging/media")

# Email configuration for staging (console backend for testing)
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)

if os.environ.get("EMAIL_HOST"):
    EMAIL_HOST = os.environ.get("EMAIL_HOST")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "staging@sabc.com")

# Security settings for staging
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = (
    os.environ.get("SESSION_COOKIE_SECURE", "True").lower() == "true"
)
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "True").lower() == "true"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Staging-specific middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # For static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Staging-specific context processor
TEMPLATES[0]["OPTIONS"]["context_processors"] += [  # noqa: F405
    "sabc.core.context_processors.staging_context",
]

# Logging configuration for staging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.environ.get("LOG_FILE", "/home/sabc-staging/logs/sabc.log"),
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": os.environ.get("LOG_LEVEL", "INFO"),
            "propagate": True,
        },
        "sabc": {
            "handlers": ["file", "console"],
            "level": os.environ.get("LOG_LEVEL", "INFO"),
            "propagate": True,
        },
    },
}

# Staging-specific settings
STAGING_ENVIRONMENT = True
STAGING_BANNER_MESSAGE = os.environ.get(
    "STAGING_WARNING", "This is a staging environment - data may be reset"
)
FAKE_DATA_ENABLED = os.environ.get("FAKE_DATA_ENABLED", "True").lower() == "true"

# Performance settings for staging
DATABASE_CONNECTION_POOL_SIZE = int(
    os.environ.get("DATABASE_CONNECTION_POOL_SIZE", "5")
)

# Third-party service configuration (use staging/test keys)
GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID", "")
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

# AWS S3 configuration (if using S3 for media files)
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")

# Development and testing features enabled in staging
ENABLE_DEBUG_TOOLBAR = DEBUG
ENABLE_FAKE_DATA_COMMANDS = True
ENABLE_ADMIN_DOCS = True

# Session configuration
SESSION_COOKIE_AGE = 3600 * 2  # 2 hours (shorter than production)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Admin interface customization for staging
ADMIN_SITE_HEADER = "SABC Staging Administration"
ADMIN_SITE_TITLE = "SABC Staging Admin"
ADMIN_INDEX_TITLE = "Welcome to SABC Staging Administration"
