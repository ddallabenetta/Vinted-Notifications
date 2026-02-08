BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS blocked_users
(
    user_id  TEXT PRIMARY KEY,
    username TEXT
);

UPDATE parameters
SET value = '1.0.5.5'
WHERE key = 'version';

COMMIT;
