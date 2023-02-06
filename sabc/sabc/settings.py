# -*- coding: utf-8 -*-
import os
from typing import Any, Optional

from django.contrib.messages import constants as messages

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY: Optional[str] = os.environ.get("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG: bool = not not os.environ.get("DJANGO_DEBUG")

ALLOWED_HOSTS: list = ["*"]

# Application definition
INSTALLED_APPS: list[str] = [
    "users",
    "polls",
    "tournaments",
    "crispy_forms",
    "django_tables2",
    "phonenumber_field",
    "django_extensions",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.contenttypes",
]
MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF: str = "sabc.urls"
TEMPLATES: list[dict] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION: str = "sabc.wsgi.application"

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
if os.environ.get("GITHUB_WORKFLOW"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "postgres",
            "USER": "postgres",
            "PASSWORD": "postgres",
            "HOST": "127.0.0.1",
            "PORT": 5432,
        }
    }
elif os.environ.get("UNITTEST"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.path.join(BASE_DIR, "db.sqlite3")}}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": os.environ.get("POSTGRES_DB", os.environ.get("POSTGRES_DB")),
            "USER": os.environ.get("POSTGRES_USER", os.environ.get("POSTGRES_USER")),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", os.environ.get("POSTGRES_PASSWORD")),
            "HOST": os.environ.get("DEPLOYMENT_HOST", "localhost"),
            "PORT": 5432,
        }
    }

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS: list[dict] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/
LANGUAGE_CODE: str = "en-us"
TIME_ZONE: str = "UTC"
USE_I18N: bool = True

# USE_L10N: bool = True
USE_TZ: bool = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
CRISPY_TEMPLATE_PACK: str = "bootstrap4"

STATIC_URL: str = "/static/"
STATICFILES_DIRS: list[str] = [os.path.join(BASE_DIR, "sabc", "static")]

MEDIA_ROOT: str = os.path.join(BASE_DIR, "media")
MEDIA_URL: str = "/media/"

LOGIN_REDIRECT_URL: str = "sabc-home"
LOGIN_URL: str = "login"

PHONENUMBER_DB_FORMAT: str = "NATIONAL"
PHONENUMBER_DEFAULT_REGION: str = "US"

# Gmail SMTP Server
EMAIL_HOST: str = "smtp.gmail.com"
EMAIL_PORT: int = 587
EMAIL_BACKEND: str = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_TLS: bool = True
DEFAULT_FROM_EMAIL: str = str(os.environ.get("DEFAULT_FROM_EMAIL"))

# Disable this in production
# File-based back-end for email for development purposes
# EMAIL_BACKEND: str = "django.core.mail.backends.filebased.EmailBackend"
# EMAIL_FILE_PATH: str = os.path.join(BASE_DIR, "sent_emails")

DEFAULT_AUTO_FIELD: str = "django.db.models.AutoField"
DJANGO_TABLES2_TEMPLATE: str = "django_tables2/bootstrap4.html"

LOGGING: dict[Any, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"), "propagate": False}
    },
}

# Make messages.error() - display in RED
MESSAGE_TAGS: dict[int, str] = {messages.ERROR: "danger"}
