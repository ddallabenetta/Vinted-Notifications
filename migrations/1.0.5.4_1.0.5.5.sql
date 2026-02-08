BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS blocked_users
(
    username TEXT PRIMARY KEY
);

UPDATE parameters
SET value = '1.0.5.5'
WHERE key = 'version';

COMMIT;
