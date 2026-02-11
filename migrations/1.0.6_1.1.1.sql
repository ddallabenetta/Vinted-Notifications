BEGIN TRANSACTION;

-- Update version to 1.1.1
-- This version adds autocomplete/search functionality for blocked users in the web UI
UPDATE parameters SET value = '1.1.1' WHERE key = 'version';

COMMIT;
