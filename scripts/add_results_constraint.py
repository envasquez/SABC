#!/usr/bin/env python3
"""
Add unique constraint to results table for UPSERT support.
This migration adds UNIQUE(tournament_id, angler_id) to results table.
"""

import logging
import sys

from sqlalchemy import text

from core.db_schema import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_results_constraint():
    """Add unique constraint to results table."""
    logger.info("Adding unique constraint to results table...")

    with engine.connect() as conn:
        try:
            # Check if constraint already exists
            result = conn.execute(
                text("""
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_name = 'results'
                    AND constraint_type = 'UNIQUE'
                    AND constraint_name = 'results_tournament_angler_unique'
                """)
            )

            if result.fetchone():
                logger.info("✅ Constraint already exists, skipping...")
                return 0

            # Add constraint
            conn.execute(
                text("""
                    ALTER TABLE results
                    ADD CONSTRAINT results_tournament_angler_unique
                    UNIQUE (tournament_id, angler_id)
                """)
            )
            conn.commit()
            logger.info("✅ Successfully added unique constraint to results table")
            return 0

        except Exception as e:
            logger.error(f"❌ Failed to add constraint: {e}")
            conn.rollback()
            return 1


if __name__ == "__main__":
    sys.exit(add_results_constraint())
