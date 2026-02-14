BEGIN TRANSACTION;

-- Create profiles table with per-profile settings
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    telegram_enabled TEXT DEFAULT 'False',
    telegram_token TEXT DEFAULT '',
    telegram_chat_id TEXT DEFAULT '',
    telegram_process_running TEXT DEFAULT 'False',
    rss_enabled TEXT DEFAULT 'False',
    rss_port TEXT DEFAULT '8080',
    rss_max_items TEXT DEFAULT '100',
    rss_process_running TEXT DEFAULT 'False',
    banwords TEXT DEFAULT '',
    message_template TEXT DEFAULT '',
    items_per_query TEXT DEFAULT '20'
);

-- Create default profile from existing parameters
INSERT INTO profiles (id, name, telegram_enabled, telegram_token, telegram_chat_id, telegram_process_running, rss_enabled, rss_port, rss_max_items, rss_process_running, banwords, message_template, items_per_query)
SELECT 1,
    'Default',
    COALESCE((SELECT value FROM parameters WHERE key = 'telegram_enabled'), 'False'),
    COALESCE((SELECT value FROM parameters WHERE key = 'telegram_token'), ''),
    COALESCE((SELECT value FROM parameters WHERE key = 'telegram_chat_id'), ''),
    COALESCE((SELECT value FROM parameters WHERE key = 'telegram_process_running'), 'False'),
    COALESCE((SELECT value FROM parameters WHERE key = 'rss_enabled'), 'False'),
    COALESCE((SELECT value FROM parameters WHERE key = 'rss_port'), '8080'),
    COALESCE((SELECT value FROM parameters WHERE key = 'rss_max_items'), '100'),
    COALESCE((SELECT value FROM parameters WHERE key = 'rss_process_running'), 'False'),
    COALESCE((SELECT value FROM parameters WHERE key = 'banwords'), ''),
    COALESCE((SELECT value FROM parameters WHERE key = 'message_template'), ''),
    COALESCE((SELECT value FROM parameters WHERE key = 'items_per_query'), '20');

-- Add profile_id to queries table
ALTER TABLE queries ADD COLUMN profile_id INTEGER DEFAULT 1;

-- Add profile_id to allowlist table
ALTER TABLE allowlist ADD COLUMN profile_id INTEGER DEFAULT 1;

-- Add profile_id to blocked_users table
ALTER TABLE blocked_users ADD COLUMN profile_id INTEGER DEFAULT 1;

-- Remove per-profile parameters from global parameters table
DELETE FROM parameters WHERE key IN (
    'telegram_enabled', 'telegram_token', 'telegram_chat_id', 'telegram_process_running',
    'rss_enabled', 'rss_port', 'rss_max_items', 'rss_process_running',
    'banwords', 'message_template', 'items_per_query'
);

-- Update version
UPDATE parameters SET value = '1.2.0' WHERE key = 'version';

COMMIT;
