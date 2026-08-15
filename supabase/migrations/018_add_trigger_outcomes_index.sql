-- Migration 018: Add critical index on trigger_outcomes.signal_id
-- Created: 2026-08-15
-- Purpose: Improve query performance for signal filtering and joining

-- UP: Create index
BEGIN;

-- Add index on signal_id for faster queries
CREATE INDEX CONCURRENTLY idx_trigger_outcomes_signal_id
  ON trigger_outcomes(signal_id);

-- Update table statistics
ANALYZE trigger_outcomes;

COMMIT;

-- DOWN: Drop index (if needed to rollback)
-- BEGIN;
--   DROP INDEX CONCURRENTLY idx_trigger_outcomes_signal_id;
--   ANALYZE trigger_outcomes;
-- COMMIT;
