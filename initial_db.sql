-- init_schema.sql
-- Initial Scheme

PRAGMA foreign_keys = ON;

/* ============================
   Tables
   ============================ */

-- Profiles table
CREATE TABLE IF NOT EXISTS profiles
(
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    name                     TEXT NOT NULL,
    telegram_enabled         TEXT DEFAULT 'False',
    telegram_token           TEXT DEFAULT '',
    telegram_chat_id         TEXT DEFAULT '',
    telegram_process_running TEXT DEFAULT 'False',
    rss_enabled              TEXT DEFAULT 'False',
    rss_port                 TEXT DEFAULT '8080',
    rss_max_items            TEXT DEFAULT '100',
    rss_process_running      TEXT DEFAULT 'False',
    banwords                 TEXT DEFAULT '',
    message_template         TEXT DEFAULT '',
    items_per_query          TEXT DEFAULT '20'
);

-- Queries table
CREATE TABLE IF NOT EXISTS queries
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    query      TEXT,
    last_item  NUMERIC,
    query_name TEXT,
    profile_id INTEGER DEFAULT 1 REFERENCES profiles(id)
);

-- Items table
CREATE TABLE IF NOT EXISTS items
(
    item      NUMERIC,
    title     TEXT,
    price     NUMERIC,
    currency  TEXT,
    timestamp NUMERIC,
    photo_url TEXT,
    query_id  INTEGER,
    username  TEXT,
    FOREIGN KEY (query_id) REFERENCES queries (id)
);

-- Allowlist table
CREATE TABLE IF NOT EXISTS allowlist
(
    country    TEXT,
    profile_id INTEGER DEFAULT 1 REFERENCES profiles(id)
);

-- Blocked users table
CREATE TABLE IF NOT EXISTS blocked_users
(
    username   TEXT,
    profile_id INTEGER DEFAULT 1 REFERENCES profiles(id)
);

-- Parameters table (global settings only)
CREATE TABLE IF NOT EXISTS parameters
(
    key   TEXT PRIMARY KEY,
    value TEXT
);

/* ============================
   Initial data
   ============================ */

-- Default profile
INSERT OR IGNORE INTO profiles (id, name) VALUES (1, 'Default');

-- Global parameters only
INSERT OR IGNORE INTO parameters (key, value)
VALUES ('version', '1.2.1'),
       ('github_url', 'https://github.com/ddallabenetta/Vinted-Notifications'),

       ('query_refresh_delay', '60'),

       ('proxy_list', ''),
       ('proxy_list_link', ''),
       ('check_proxies', 'False'),
       ('last_proxy_check_time', '0'),

       ('schedule_enabled', 'False'),
       ('schedule_start_time', '08:00'),
       ('schedule_end_time', '01:00'),

       ('timezone', 'Europe/Rome'),
       ('user_agents', '[]'),
       ('default_headers', '{}');
