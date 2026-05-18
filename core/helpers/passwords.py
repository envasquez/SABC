"""Password hashing helpers."""

import os

import bcrypt


def bcrypt_gensalt() -> bytes:
    """Generate a bcrypt salt.

    The work factor defaults to 12 (production-grade strength). The test suite
    sets ``BCRYPT_ROUNDS=4`` to keep hashing and verification fast — bcrypt
    encodes the cost inside the hash, so a low-cost test hash is also cheap to
    verify. This must never be lowered in a production environment.
    """
    rounds = int(os.environ.get("BCRYPT_ROUNDS", "12"))

    # Only development and test environments may use a sub-12 work factor
    # (the test suite relies on BCRYPT_ROUNDS=4 for speed). Mirrors the
    # ENVIRONMENT allowlist used in app_setup.py (_DEV_SECRET_FALLBACK_ENVS).
    # Any other environment (production, staging, unset) enforces a floor of 12.
    env = os.environ.get("ENVIRONMENT", "development")
    if env not in ("development", "test"):
        rounds = max(rounds, 12)

    return bcrypt.gensalt(rounds=rounds)
