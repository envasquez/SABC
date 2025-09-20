#!/usr/bin/env python3
"""
Common utilities for SABC scripts.
Provides shared functionality to eliminate duplication across scripts.
"""

import logging
import os
import sys
from typing import Optional

# Add project root to path - shared by all scripts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Setup standardized logging for scripts."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def ensure_database_url(default_url: str = "postgresql://postgres:dev123@localhost:5432/sabc") -> str:
    """Ensure DATABASE_URL is set, using default if not provided."""
    database_url = os.environ.get("DATABASE_URL", default_url)
    os.environ["DATABASE_URL"] = database_url
    return database_url


def check_admin_exists(email: str = "admin@sabc.com") -> bool:
    """Check if admin user exists in database."""
    try:
        existing = db("SELECT id FROM anglers WHERE email = :email", {"email": email})
        return bool(existing)
    except Exception:
        return False