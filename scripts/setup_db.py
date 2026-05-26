"""Initialize the SABC database via Alembic migrations.

Schema is owned by Alembic — see docs/DATABASE_MIGRATIONS.md. This script is
a thin wrapper that runs `alembic upgrade head` against the configured
DATABASE_URL so first-time setup is a single command. Iterative schema
changes still go through alembic revision/upgrade.
"""

import logging
import os
import sys

from alembic import command
from alembic.config import Config


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("setup_db")

    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL is not set — refusing to run.")
        return 1

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(repo_root, "alembic.ini"))

    logger.info("Running alembic upgrade head…")
    command.upgrade(alembic_cfg, "head")
    logger.info("Database setup complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
