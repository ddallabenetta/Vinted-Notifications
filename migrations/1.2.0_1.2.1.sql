BEGIN TRANSACTION;

UPDATE parameters
SET value = '1.2.1'
WHERE key = 'version';

COMMIT;
