BEGIN TRANSACTION;

-- Add timezone parameter for correct timestamp display
INSERT OR IGNORE INTO parameters (key, value) VALUES ('timezone', 'Europe/Rome');

-- Update version to 1.1.2
-- This version adds proper timezone handling for timestamps and scheduler
UPDATE parameters SET value = '1.1.2' WHERE key = 'version';

COMMIT;
