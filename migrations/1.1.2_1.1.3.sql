BEGIN TRANSACTION;

-- Update version to 1.1.3
-- This version fixes a bug where the item extractor or dispatcher processes
-- could silently crash on an unexpected exception, causing the pipeline to stop
-- delivering notifications while the scraper continued to run normally.
UPDATE parameters SET value = '1.1.3' WHERE key = 'version';

COMMIT;
