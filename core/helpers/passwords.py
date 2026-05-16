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
    return bcrypt.gensalt(rounds=rounds)
