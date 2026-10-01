"""Tests for the DATABASE_URL driver pinning in core.db_schema.engine.

SQLAlchemy 2.1 changed the default DBAPI for a bare ``postgresql://`` URL from
psycopg2 to psycopg (v3). We install psycopg2-binary, so a bare URL blows up at
import time with ModuleNotFoundError under 2.1+. These tests lock in the
normalization that keeps the deployed URL pointed at psycopg2.
"""

import pytest

from core.db_schema.engine import pin_psycopg2_driver


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "postgresql://sabc_user:pw@postgres:5432/sabc",
            "postgresql+psycopg2://sabc_user:pw@postgres:5432/sabc",
        ),
        (
            "postgres://sabc_user:pw@postgres:5432/sabc",
            "postgresql+psycopg2://sabc_user:pw@postgres:5432/sabc",
        ),
    ],
)
def test_bare_postgres_urls_get_the_psycopg2_driver(url: str, expected: str) -> None:
    assert pin_psycopg2_driver(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg2://sabc_user:pw@postgres:5432/sabc",
        "postgresql+psycopg://sabc_user:pw@postgres:5432/sabc",
        "sqlite:///sabc.db",
    ],
)
def test_explicit_drivers_are_left_alone(url: str) -> None:
    assert pin_psycopg2_driver(url) == url
