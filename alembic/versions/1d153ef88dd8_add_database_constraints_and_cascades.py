"""Add database constraints and cascades

This migration adds:
1. Unique constraints to prevent duplicate poll options and double voting
2. Check constraints to validate positive numeric values
3. Foreign key CASCADE and SET NULL behaviors for data integrity

Revision ID: 1d153ef88dd8
Revises: b6af1117804a
Create Date: 2025-10-09 19:05:07.889504

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1d153ef88dd8"
down_revision: Union[str, None] = "b6af1117804a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database constraints for data integrity."""
    conn = op.get_bind()

    # First, clean up any orphaned foreign key references in the database
    # This is necessary because the production database may have been created without foreign keys
    print("Cleaning up orphaned references...")

    # Clean up orphaned tournament references
    result = conn.execute(
        sa.text(
            "UPDATE tournaments SET event_id = NULL WHERE event_id IS NOT NULL AND event_id NOT IN (SELECT id FROM events)"
        )
    )
    if result.rowcount > 0:
        print(f"  Fixed {result.rowcount} orphaned tournaments.event_id references")

    result = conn.execute(
        sa.text(
            "UPDATE tournaments SET poll_id = NULL WHERE poll_id IS NOT NULL AND poll_id NOT IN (SELECT id FROM polls)"
        )
    )
    if result.rowcount > 0:
        print(f"  Fixed {result.rowcount} orphaned tournaments.poll_id references")

    result = conn.execute(
        sa.text(
            "UPDATE tournaments SET lake_id = NULL WHERE lake_id IS NOT NULL AND lake_id NOT IN (SELECT id FROM lakes)"
        )
    )
    if result.rowcount > 0:
        print(f"  Fixed {result.rowcount} orphaned tournaments.lake_id references")

    result = conn.execute(
        sa.text(
            "UPDATE tournaments SET ramp_id = NULL WHERE ramp_id IS NOT NULL AND ramp_id NOT IN (SELECT id FROM ramps)"
        )
    )
    if result.rowcount > 0:
        print(f"  Fixed {result.rowcount} orphaned tournaments.ramp_id references")

    result = conn.execute(
        sa.text(
            "UPDATE tournaments SET created_by = NULL WHERE created_by IS NOT NULL AND created_by NOT IN (SELECT id FROM anglers)"
        )
    )
    if result.rowcount > 0:
        print(f"  Fixed {result.rowcount} orphaned tournaments.created_by references")

    # Clean up orphaned poll references
    result = conn.execute(
        sa.text(
            "UPDATE polls SET event_id = NULL WHERE event_id IS NOT NULL AND event_id NOT IN (SELECT id FROM events)"
        )
    )
    if result.rowcount > 0:
        print(f"  Fixed {result.rowcount} orphaned polls.event_id references")

    result = conn.execute(
        sa.text(
            "UPDATE polls SET created_by = NULL WHERE created_by IS NOT NULL AND created_by NOT IN (SELECT id FROM anglers)"
        )
    )
    if result.rowcount > 0:
        print(f"  Fixed {result.rowcount} orphaned polls.created_by references")

    # Clean up orphaned ramp references
    result = conn.execute(
        sa.text(
            "DELETE FROM ramps WHERE lake_id IS NOT NULL AND lake_id NOT IN (SELECT id FROM lakes)"
        )
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned ramps (invalid lake_id)")

    # Clean up orphaned news references
    result = conn.execute(
        sa.text(
            "UPDATE news SET author_id = NULL WHERE author_id IS NOT NULL AND author_id NOT IN (SELECT id FROM anglers)"
        )
    )
    if result.rowcount > 0:
        print(f"  Fixed {result.rowcount} orphaned news.author_id references")

    # Clean up orphaned poll data
    result = conn.execute(
        sa.text("DELETE FROM poll_votes WHERE poll_id NOT IN (SELECT id FROM polls)")
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned poll votes (invalid poll_id)")

    result = conn.execute(
        sa.text(
            "DELETE FROM poll_votes WHERE option_id IS NOT NULL AND option_id NOT IN (SELECT id FROM poll_options)"
        )
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned poll votes (invalid option_id)")

    result = conn.execute(
        sa.text("DELETE FROM poll_votes WHERE angler_id NOT IN (SELECT id FROM anglers)")
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned poll votes (invalid angler_id)")

    result = conn.execute(
        sa.text("DELETE FROM poll_options WHERE poll_id NOT IN (SELECT id FROM polls)")
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned poll options (invalid poll_id)")

    # Clean up orphaned results
    result = conn.execute(
        sa.text("DELETE FROM results WHERE tournament_id NOT IN (SELECT id FROM tournaments)")
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned results (invalid tournament_id)")

    result = conn.execute(
        sa.text("DELETE FROM results WHERE angler_id NOT IN (SELECT id FROM anglers)")
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned results (invalid angler_id)")

    result = conn.execute(
        sa.text("DELETE FROM team_results WHERE tournament_id NOT IN (SELECT id FROM tournaments)")
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned team results (invalid tournament_id)")

    result = conn.execute(
        sa.text(
            "DELETE FROM team_results WHERE angler1_id NOT IN (SELECT id FROM anglers) OR angler2_id NOT IN (SELECT id FROM anglers)"
        )
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned team results (invalid angler_id)")

    # Clean up orphaned officer positions
    result = conn.execute(
        sa.text("DELETE FROM officer_positions WHERE angler_id NOT IN (SELECT id FROM anglers)")
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned officer positions (invalid angler_id)")

    # Clean up orphaned password reset tokens
    result = conn.execute(
        sa.text("DELETE FROM password_reset_tokens WHERE user_id NOT IN (SELECT id FROM anglers)")
    )
    if result.rowcount > 0:
        print(f"  Deleted {result.rowcount} orphaned password reset tokens (invalid user_id)")

    print("Orphaned reference cleanup complete!")

    # Add unique constraint on poll_options to prevent duplicate option text per poll
    conn.execute(
        sa.text(
            """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_poll_option_text') THEN
                ALTER TABLE poll_options ADD CONSTRAINT uq_poll_option_text UNIQUE (poll_id, option_text);
            END IF;
        END$$;
    """
        )
    )

    # Replace existing poll_votes unique constraint with simpler one
    conn.execute(
        sa.text(
            "ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS poll_votes_poll_id_option_id_angler_id_key"
        )
    )
    conn.execute(sa.text("ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS unique_poll_angler"))
    conn.execute(
        sa.text(
            """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_poll_vote_angler') THEN
                ALTER TABLE poll_votes ADD CONSTRAINT uq_poll_vote_angler UNIQUE (poll_id, angler_id);
            END IF;
        END$$;
    """
        )
    )

    # Add check constraints to results table
    conn.execute(
        sa.text(
            """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_result_num_fish_positive') THEN
                ALTER TABLE results ADD CONSTRAINT ck_result_num_fish_positive CHECK (num_fish >= 0);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_result_total_weight_positive') THEN
                ALTER TABLE results ADD CONSTRAINT ck_result_total_weight_positive CHECK (total_weight >= 0);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_result_big_bass_weight_positive') THEN
                ALTER TABLE results ADD CONSTRAINT ck_result_big_bass_weight_positive CHECK (big_bass_weight >= 0);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_result_dead_fish_penalty_positive') THEN
                ALTER TABLE results ADD CONSTRAINT ck_result_dead_fish_penalty_positive CHECK (dead_fish_penalty >= 0);
            END IF;
        END$$;
    """
        )
    )

    # Add check constraint to team_results table
    conn.execute(
        sa.text(
            """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_team_result_total_weight_positive') THEN
                ALTER TABLE team_results ADD CONSTRAINT ck_team_result_total_weight_positive CHECK (total_weight >= 0);
            END IF;
        END$$;
    """
        )
    )

    # Add foreign keys with CASCADE/SET NULL behavior
    # Poll system CASCADE deletes
    conn.execute(
        sa.text("ALTER TABLE poll_options DROP CONSTRAINT IF EXISTS poll_options_poll_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE poll_options ADD CONSTRAINT poll_options_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE"
        )
    )

    conn.execute(
        sa.text("ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS poll_votes_poll_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE poll_votes ADD CONSTRAINT poll_votes_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE"
        )
    )

    conn.execute(
        sa.text("ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS poll_votes_option_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE poll_votes ADD CONSTRAINT poll_votes_option_id_fkey FOREIGN KEY (option_id) REFERENCES poll_options(id) ON DELETE CASCADE"
        )
    )

    conn.execute(
        sa.text("ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS poll_votes_angler_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE poll_votes ADD CONSTRAINT poll_votes_angler_id_fkey FOREIGN KEY (angler_id) REFERENCES anglers(id) ON DELETE CASCADE"
        )
    )

    # Tournament results CASCADE deletes
    conn.execute(
        sa.text("ALTER TABLE results DROP CONSTRAINT IF EXISTS results_tournament_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE results ADD CONSTRAINT results_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE"
        )
    )

    conn.execute(sa.text("ALTER TABLE results DROP CONSTRAINT IF EXISTS results_angler_id_fkey"))
    conn.execute(
        sa.text(
            "ALTER TABLE results ADD CONSTRAINT results_angler_id_fkey FOREIGN KEY (angler_id) REFERENCES anglers(id) ON DELETE CASCADE"
        )
    )

    conn.execute(
        sa.text(
            "ALTER TABLE team_results DROP CONSTRAINT IF EXISTS team_results_tournament_id_fkey"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE team_results ADD CONSTRAINT team_results_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE"
        )
    )

    conn.execute(
        sa.text("ALTER TABLE team_results DROP CONSTRAINT IF EXISTS team_results_angler1_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE team_results ADD CONSTRAINT team_results_angler1_id_fkey FOREIGN KEY (angler1_id) REFERENCES anglers(id) ON DELETE CASCADE"
        )
    )

    conn.execute(
        sa.text("ALTER TABLE team_results DROP CONSTRAINT IF EXISTS team_results_angler2_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE team_results ADD CONSTRAINT team_results_angler2_id_fkey FOREIGN KEY (angler2_id) REFERENCES anglers(id) ON DELETE CASCADE"
        )
    )

    # Event CASCADE deletes
    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_event_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE tournaments ADD CONSTRAINT tournaments_event_id_fkey FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE"
        )
    )

    # Lake CASCADE deletes
    conn.execute(sa.text("ALTER TABLE ramps DROP CONSTRAINT IF EXISTS ramps_lake_id_fkey"))
    conn.execute(
        sa.text(
            "ALTER TABLE ramps ADD CONSTRAINT ramps_lake_id_fkey FOREIGN KEY (lake_id) REFERENCES lakes(id) ON DELETE CASCADE"
        )
    )

    # Angler CASCADE deletes
    conn.execute(
        sa.text(
            "ALTER TABLE officer_positions DROP CONSTRAINT IF EXISTS officer_positions_angler_id_fkey"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE officer_positions ADD CONSTRAINT officer_positions_angler_id_fkey FOREIGN KEY (angler_id) REFERENCES anglers(id) ON DELETE CASCADE"
        )
    )

    conn.execute(
        sa.text(
            "ALTER TABLE password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_user_id_fkey"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE password_reset_tokens ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES anglers(id) ON DELETE CASCADE"
        )
    )

    # SET NULL for optional relationships
    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_poll_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE tournaments ADD CONSTRAINT tournaments_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE SET NULL"
        )
    )

    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_lake_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE tournaments ADD CONSTRAINT tournaments_lake_id_fkey FOREIGN KEY (lake_id) REFERENCES lakes(id) ON DELETE SET NULL"
        )
    )

    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_ramp_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE tournaments ADD CONSTRAINT tournaments_ramp_id_fkey FOREIGN KEY (ramp_id) REFERENCES ramps(id) ON DELETE SET NULL"
        )
    )

    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_created_by_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE tournaments ADD CONSTRAINT tournaments_created_by_fkey FOREIGN KEY (created_by) REFERENCES anglers(id) ON DELETE SET NULL"
        )
    )

    conn.execute(sa.text("ALTER TABLE polls DROP CONSTRAINT IF EXISTS polls_created_by_fkey"))
    conn.execute(
        sa.text(
            "ALTER TABLE polls ADD CONSTRAINT polls_created_by_fkey FOREIGN KEY (created_by) REFERENCES anglers(id) ON DELETE SET NULL"
        )
    )

    conn.execute(sa.text("ALTER TABLE polls DROP CONSTRAINT IF EXISTS polls_event_id_fkey"))
    conn.execute(
        sa.text(
            "ALTER TABLE polls ADD CONSTRAINT polls_event_id_fkey FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL"
        )
    )

    conn.execute(sa.text("ALTER TABLE news DROP CONSTRAINT IF EXISTS news_author_id_fkey"))
    conn.execute(
        sa.text(
            "ALTER TABLE news ADD CONSTRAINT news_author_id_fkey FOREIGN KEY (author_id) REFERENCES anglers(id) ON DELETE SET NULL"
        )
    )


def downgrade() -> None:
    """Remove database constraints."""
    conn = op.get_bind()

    # Remove check constraints
    conn.execute(
        sa.text(
            "ALTER TABLE team_results DROP CONSTRAINT IF EXISTS ck_team_result_total_weight_positive"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE results DROP CONSTRAINT IF EXISTS ck_result_dead_fish_penalty_positive"
        )
    )
    conn.execute(
        sa.text("ALTER TABLE results DROP CONSTRAINT IF EXISTS ck_result_big_bass_weight_positive")
    )
    conn.execute(
        sa.text("ALTER TABLE results DROP CONSTRAINT IF EXISTS ck_result_total_weight_positive")
    )
    conn.execute(
        sa.text("ALTER TABLE results DROP CONSTRAINT IF EXISTS ck_result_num_fish_positive")
    )

    # Remove unique constraints
    conn.execute(sa.text("ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS uq_poll_vote_angler"))
    conn.execute(sa.text("ALTER TABLE poll_options DROP CONSTRAINT IF EXISTS uq_poll_option_text"))

    # Remove foreign keys
    conn.execute(sa.text("ALTER TABLE news DROP CONSTRAINT IF EXISTS news_author_id_fkey"))
    conn.execute(sa.text("ALTER TABLE polls DROP CONSTRAINT IF EXISTS polls_event_id_fkey"))
    conn.execute(sa.text("ALTER TABLE polls DROP CONSTRAINT IF EXISTS polls_created_by_fkey"))
    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_created_by_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_ramp_id_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_lake_id_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_poll_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE password_reset_tokens DROP CONSTRAINT IF EXISTS password_reset_tokens_user_id_fkey"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE officer_positions DROP CONSTRAINT IF EXISTS officer_positions_angler_id_fkey"
        )
    )
    conn.execute(sa.text("ALTER TABLE ramps DROP CONSTRAINT IF EXISTS ramps_lake_id_fkey"))
    conn.execute(
        sa.text("ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS tournaments_event_id_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE team_results DROP CONSTRAINT IF EXISTS team_results_angler2_id_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE team_results DROP CONSTRAINT IF EXISTS team_results_angler1_id_fkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE team_results DROP CONSTRAINT IF EXISTS team_results_tournament_id_fkey"
        )
    )
    conn.execute(sa.text("ALTER TABLE results DROP CONSTRAINT IF EXISTS results_angler_id_fkey"))
    conn.execute(
        sa.text("ALTER TABLE results DROP CONSTRAINT IF EXISTS results_tournament_id_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS poll_votes_angler_id_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS poll_votes_option_id_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE poll_votes DROP CONSTRAINT IF EXISTS poll_votes_poll_id_fkey")
    )
    conn.execute(
        sa.text("ALTER TABLE poll_options DROP CONSTRAINT IF EXISTS poll_options_poll_id_fkey")
    )
