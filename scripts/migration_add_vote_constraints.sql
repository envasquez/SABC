-- Migration: Add unique constraints to prevent duplicate votes and team results
-- Date: 2025-10-05
-- Phase 1: Emergency bug fixes

-- Add unique constraint for poll votes (prevents duplicate voting via race condition)
DO $$
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'unique_poll_angler'
    ) THEN
        -- First, remove any existing duplicates (keep the earliest vote)
        DELETE FROM poll_votes a
        USING poll_votes b
        WHERE a.id > b.id
          AND a.poll_id = b.poll_id
          AND a.angler_id = b.angler_id;

        -- Add the unique constraint
        ALTER TABLE poll_votes
        ADD CONSTRAINT unique_poll_angler UNIQUE (poll_id, angler_id);

        RAISE NOTICE 'Added unique constraint: unique_poll_angler';
    ELSE
        RAISE NOTICE 'Constraint unique_poll_angler already exists';
    END IF;
END $$;

-- Add unique constraint for team results (prevents duplicate team entries)
DO $$
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'unique_tournament_team'
    ) THEN
        -- Remove duplicates if any exist (keep the earliest entry)
        DELETE FROM team_results a
        USING team_results b
        WHERE a.id > b.id
          AND a.tournament_id = b.tournament_id
          AND a.angler1_id = b.angler1_id
          AND a.angler2_id = b.angler2_id;

        -- Add the unique constraint
        ALTER TABLE team_results
        ADD CONSTRAINT unique_tournament_team
        UNIQUE (tournament_id, angler1_id, angler2_id);

        RAISE NOTICE 'Added unique constraint: unique_tournament_team';
    ELSE
        RAISE NOTICE 'Constraint unique_tournament_team already exists';
    END IF;
END $$;

-- Verify constraints were added
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conname IN ('unique_poll_angler', 'unique_tournament_team')
ORDER BY conname;
