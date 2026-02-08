# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Vinted-Notifications is a real-time notification system for Vinted listings. It monitors search queries across all Vinted country domains and delivers notifications via Telegram and/or RSS feed. The application uses a multiprocessing architecture with separate processes for scraping, dispatching, and plugin services.

## Development Commands

### Running the Application

```bash
# Self-build (requires Python 3.11+)
pip install -r requirements.txt
python vinted_notifications.py

# Docker Compose (recommended)
docker-compose up -d

# Docker Run
docker run -d \
  --name vinted-notifications \
  -p 8000:8000 \
  -p 8080:8080 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  --restart unless-stopped \
  daninotfound/vinted-notifications:latest
```

### Access Points

- Web UI: http://localhost:8000
- RSS Feed: http://localhost:8080 (when enabled)

### Database

- SQLite database located at: `./data/vinted_notifications.db`
- Database schema in: `initial_db.sql`
- Migrations in: `migrations/` directory (format: `{old_version}_{new_version}.sql`)
- Use `db.py` functions for all database operations (never direct SQL in other modules)

### Logs

- Application logs stored in: `logs/vinted.log`
- Access via Web UI at: http://localhost:8000/logs
- Configured through `logger.py` module

## Architecture

### Multiprocessing Pipeline

The application uses multiprocessing with queues for communication between processes:

```
vinted_notifications.py (main orchestrator)
├── scraper_process (scheduled via APScheduler)
│   └── Calls core.process_items() → puts items in items_queue
├── item_extractor_process
│   └── Calls core.clear_item_queue() → filters/validates items → puts in new_items_queue
├── dispatcher_process
│   └── Takes from new_items_queue → distributes to plugin queues (rss_queue, telegram_queue)
├── telegram_bot_process (optional, controlled via DB)
│   └── LeRobot class from telegram_bot_plugin/telegram_bot.py
├── rss_feed_process (optional, controlled via DB)
│   └── rss_feed.py from rss_feed_plugin/
└── web_ui_process (always runs)
    └── Flask app from web_ui_plugin/web_ui.py
```

### Process Management

- Processes are managed dynamically based on database parameters
- `monitor_processes()` function runs every 5 seconds to start/stop plugin processes
- Start/stop controlled via `telegram_process_running` and `rss_process_running` DB parameters
- Query refresh delay can be changed dynamically (kills and restarts scraper process)

### Core Modules

#### vinted_notifications.py
Main orchestrator. Handles process lifecycle, monitors database for config changes, manages multiprocessing queues.

#### core.py
Business logic for:
- Query processing (parsing Vinted URLs, validating, adding/removing queries)
- Item filtering (allowlist country check, banwords, deduplication)
- Message formatting using templates from DB
- Version checking against GitHub releases

#### db.py
Database abstraction layer. All database operations go through this module:
- Query CRUD operations
- Item storage and retrieval
- Allowlist management
- Parameter get/set (configuration storage)
- Statistics (items per day, counts)

#### pyVintedVN/
Custom Vinted API wrapper (fork/modification of pyVinted):
- `vinted.py`: Main entry point, exposes Items class
- `items/items.py`: Search functionality, URL parsing
- `items/item.py`: Item data model
- `requester.py`: HTTP client with retry logic, cookie management, proxy support
- `settings.py`: API URLs and endpoints

#### proxies.py
Proxy management system:
- Fetches proxies from list or URL
- Parallel proxy validation using ThreadPoolExecutor
- Caching mechanism (rechecks every 6 hours)
- Integrates with requester.py for rotation

#### logger.py
Centralized logging configuration. Uses rotating file handler.

### Web UI Plugin (Flask)

Located in `web_ui_plugin/`:
- `web_ui.py`: Flask routes and application logic
- `templates/`: Jinja2 templates
- `static/`: CSS/JS assets
- Routes: `/`, `/queries`, `/items`, `/config`, `/allowlist`, `/logs`
- API endpoints: `/control/<process>/<action>`, `/api/logs`

### Query Processing

1. **Query Format**: Full Vinted search URLs with filters (e.g., `https://www.vinted.fr/catalog?search_text=nike&price_to=50`)
2. **URL Processing** (in `core.process_query()`):
   - Converts brand URLs (`/brand/123-nike`) to catalog format
   - Forces `order=newest_first`
   - Removes temporal parameters (`time`, `search_id`, `page`)
   - Checks for duplicates before adding
3. **Scraping**: pyVintedVN makes API calls to Vinted's internal API
4. **Filtering**: Items filtered by:
   - Timestamp (only new items since last check)
   - Allowlist (optional country filtering via `get_user_country()`)
   - Banwords (case-insensitive title matching, delimiter: `|||`)
   - Deduplication (checks `items` table by item ID)

### Configuration

All configuration stored in `parameters` table:
- Telegram: `telegram_enabled`, `telegram_token`, `telegram_chat_id`
- RSS: `rss_enabled`, `rss_port`, `rss_max_items`
- System: `items_per_query`, `query_refresh_delay`, `banwords`
- Proxies: `proxy_list`, `proxy_list_link`, `check_proxies`
- Advanced: `message_template`, `user_agents` (JSON array), `default_headers` (JSON object)

### Important Patterns

1. **Database as Source of Truth**: Process state, configuration changes, all managed via DB parameters
2. **No Direct SQL**: Always use `db.py` functions for database operations
3. **Proxy Rotation**: Managed automatically by `requester.py` calling `proxies.configure_proxy()`
4. **Error Handling**: All processes have try/except with logging, graceful degradation
5. **Multiprocessing Queues**: Never share database connections across processes
6. **Migration System**: Automatic migration runner checks version and applies SQL files from `migrations/`

## Common Pitfalls

- **SQLite Locking**: Database accessed from multiple processes. Keep transactions short.
- **Process Termination**: Must properly join() all processes on shutdown to avoid zombies
- **Vinted API Changes**: pyVintedVN may need updates if Vinted changes their API structure
- **Cookie Expiry**: Requester handles 401 errors with automatic retry and cookie refresh
- **Proxy Validation**: Checking many proxies can be slow; use `check_proxies=False` for performance

## Key Files to Check

When debugging or implementing features:
- Process issues → `vinted_notifications.py`
- Query/item logic → `core.py`
- Database operations → `db.py`
- Web UI issues → `web_ui_plugin/web_ui.py`
- Vinted API changes → `pyVintedVN/requester.py`, `pyVintedVN/items/items.py`
- Telegram bot → `telegram_bot_plugin/telegram_bot.py`

## Version and Migration

Current version tracked in `parameters` table. Migrations follow naming: `{old}__{new}.sql`. On startup, `vinted_notifications.py` applies all pending migrations sequentially.
