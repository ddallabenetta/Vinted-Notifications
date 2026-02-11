BEGIN TRANSACTION;

INSERT OR IGNORE INTO parameters (key, value) VALUES ('schedule_enabled', 'False');
INSERT OR IGNORE INTO parameters (key, value) VALUES ('schedule_start_time', '08:00');
INSERT OR IGNORE INTO parameters (key, value) VALUES ('schedule_end_time', '01:00');

UPDATE parameters SET value = '1.0.6' WHERE key = 'version';

COMMIT;
