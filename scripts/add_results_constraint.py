import logging
import sys

from core.db_schema import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_results_constraint():
    logger.info("Adding unique constraint to results table...")

    with engine.connect() as conn:
        try:
            result = conn.execute()

            if result.fetchone():
                logger.info("✅ Constraint already exists, skipping...")
                return 0

            conn.execute()
            conn.commit()
            logger.info("✅ Successfully added unique constraint to results table")
            return 0

        except Exception as e:
            logger.error(f"❌ Failed to add constraint: {e}")
            conn.rollback()
            return 1


if __name__ == "__main__":
    sys.exit(add_results_constraint())
