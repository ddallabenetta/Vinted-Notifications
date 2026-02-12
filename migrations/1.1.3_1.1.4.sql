BEGIN TRANSACTION;

-- Add username column to items table for block/unblock functionality
ALTER TABLE items ADD COLUMN username TEXT;

-- Update version to 1.1.4
UPDATE parameters SET value = '1.1.4' WHERE key = 'version';

COMMIT;
