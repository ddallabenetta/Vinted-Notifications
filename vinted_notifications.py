import multiprocessing
import os
import time

from apscheduler.schedulers.background import BackgroundScheduler

import core
import db
import timezone_utils
from logger import get_logger
from rss_feed_plugin.rss_feed import rss_feed_process
from web_ui_plugin.web_ui import web_ui_process

# Get logger for this module
logger = get_logger(__name__)


def ensure_database_ready():
    os.makedirs("./data", exist_ok=True)

    if not os.path.exists(db.DB_PATH):
        logger.info("Database not found, creating a new one.")
        db.create_or_update_sqlite_db("initial_db.sql")
        logger.info("Database created successfully")
        return

    if not db.table_exists("parameters"):
        logger.warning(
            "Database exists but is missing the parameters table. "
            "Applying base schema initialization."
        )
        db.create_or_update_sqlite_db("initial_db.sql")


# Starting sequence
# Db check
ensure_database_ready()

# Global process references
# Per-profile processes: dict of profile_id -> process
telegram_processes = {}
rss_processes = {}
scrape_process = None
current_query_refresh_delay = None
schedule_paused = False


def scraper_process(items_queue):
    logger.info("Scrape process started")

    # Get the query refresh delay from the database
    current_query_refresh_delay = int(db.get_parameter("query_refresh_delay"))
    logger.info(f"Using query refresh delay of {current_query_refresh_delay} seconds")

    scraper_scheduler = BackgroundScheduler()
    scraper_scheduler.add_job(
        core.process_items,
        "interval",
        seconds=current_query_refresh_delay,
        args=[items_queue],
        name="scraper",
    )
    scraper_scheduler.start()
    try:
        # Keep the process running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scraper_scheduler.shutdown()
        logger.info("Scrape process stopped")


def item_extractor(items_queue, new_items_queue):
    logger.info("Item extractor process started")
    try:
        while True:
            try:
                # Check if there's an item in the queue
                core.clear_item_queue(items_queue, new_items_queue)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                logger.error(
                    f"Error in item extractor (will retry): {e}", exc_info=True
                )
            time.sleep(0.1)  # Small sleep to prevent high CPU usage
    except (KeyboardInterrupt, SystemExit):
        logger.info("Consumer process stopped")


def dispatcher_function(input_queue, telegram_queues, rss_queues):
    """
    Dispatcher that routes items to the correct profile's telegram/rss queues.

    Args:
        input_queue: Queue with items including profile_id
        telegram_queues: dict of profile_id -> Queue for telegram
        rss_queues: dict of profile_id -> Queue for RSS
    """
    logger.info("Dispatcher process started")
    try:
        while True:
            try:
                # Get from input queue - now includes profile_id
                item = input_queue.get()
                content, url, text, buy_url, buy_text, profile_id = item

                # Route to the correct profile's queues
                if profile_id in telegram_queues:
                    telegram_queues[profile_id].put((content, url, text, buy_url, buy_text))

                if profile_id in rss_queues:
                    rss_queues[profile_id].put((content, url, text, buy_url, buy_text))
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                logger.error(
                    f"Error in dispatcher process (will retry): {e}", exc_info=True
                )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dispatcher process stopped")


def telegram_bot_process(queue, profile_id):
    logger.info(f"Telegram bot process started for profile {profile_id}")
    import asyncio

    try:
        # Import LeRobot
        from telegram_bot_plugin.telegram_bot import LeRobot

        # The bot will run with app.run_polling() which is already in the module
        asyncio.run(LeRobot(queue, profile_id))
    except (KeyboardInterrupt, SystemExit):
        logger.info(f"Telegram bot process stopped for profile {profile_id}")
    except Exception as e:
        logger.error(f"Error in telegram bot process (profile {profile_id}): {e}", exc_info=True)


def is_within_schedule():
    """Check if the current time is within the configured active schedule.
    Returns True if schedule is disabled or current time is within the active window.
    Uses the configured local timezone for accurate time comparison."""
    try:
        schedule_enabled = db.get_parameter("schedule_enabled") == "True"
        if not schedule_enabled:
            return True

        start_str = db.get_parameter("schedule_start_time")
        end_str = db.get_parameter("schedule_end_time")
        if not start_str or not end_str:
            return True

        # Use local timezone for schedule comparison
        now = timezone_utils.local_now().time()
        start = timezone_utils.parse_time_string(start_str)
        end = timezone_utils.parse_time_string(end_str)

        if start <= end:
            # Normal range (e.g. 08:00 - 23:00)
            return start <= now <= end
        else:
            # Crosses midnight (e.g. 08:00 - 01:00)
            return now >= start or now <= end
    except Exception as e:
        logger.error(f"Error checking schedule: {e}", exc_info=True)
        return True  # Default to active on error


def check_refresh_delay(items_queue):
    """Check if the query refresh delay has changed and update the scheduler if needed"""
    global scrape_process, current_query_refresh_delay

    # Check if the scheduler is running

    if scrape_process is None or not scrape_process.is_alive():
        return

    # Get the current value from the database
    try:
        new_delay = int(db.get_parameter("query_refresh_delay"))

        # If the delay has changed, update the scheduler
        if new_delay != current_query_refresh_delay:
            logger.info(
                f"Query refresh delay changed from {current_query_refresh_delay} to {new_delay} seconds"
            )

            # Update the global variable
            current_query_refresh_delay = new_delay

            # Remove the existing job and add a new one with the updated interval
            scrape_process.terminate()
            scrape_process.join()
            scrape_process = multiprocessing.Process(
                target=scraper_process, args=(items_queue,)
            )
            scrape_process.start()

            logger.info(
                f"Scheduler updated with new refresh delay of {new_delay} seconds"
            )
    except Exception as e:
        logger.error(f"Error updating refresh delay: {e}", exc_info=True)


def monitor_processes(items_queue, telegram_queues, rss_queues, queue_manager):
    global telegram_processes, rss_processes, scrape_process, schedule_paused

    # Check schedule
    within_schedule = is_within_schedule()

    if not within_schedule and not schedule_paused:
        # Entering pause: stop the scraper
        logger.info("Outside active schedule, pausing scraper")
        if scrape_process is not None and scrape_process.is_alive():
            scrape_process.terminate()
            scrape_process.join()
            scrape_process = None
        schedule_paused = True
    elif within_schedule and schedule_paused:
        # Resuming: restart the scraper
        logger.info("Within active schedule, resuming scraper")
        scrape_process = multiprocessing.Process(
            target=scraper_process, args=(items_queue,)
        )
        scrape_process.start()
        schedule_paused = False

    # Check if the query refresh delay has changed (only when not paused)
    if not schedule_paused:
        check_refresh_delay(items_queue)

    ### PER-PROFILE TELEGRAM AND RSS ###
    profiles = db.get_profiles()

    for profile_id, profile_name in profiles:
        profile_settings = db.get_all_profile_settings(profile_id)

        ### TELEGRAM ###
        telegram_should_run = profile_settings.get("telegram_process_running") == "True"
        telegram_token = profile_settings.get("telegram_token", "")
        telegram_chat_id = profile_settings.get("telegram_chat_id", "")
        if not telegram_token or not telegram_chat_id:
            telegram_should_run = False

        telegram_is_running = (
            profile_id in telegram_processes
            and telegram_processes[profile_id] is not None
            and telegram_processes[profile_id].is_alive()
        )

        # Ensure queue exists for this profile
        if profile_id not in telegram_queues:
            telegram_queues[profile_id] = queue_manager.Queue()

        if telegram_should_run and not telegram_is_running:
            logger.info(f"Starting telegram bot process for profile '{profile_name}' (id={profile_id})")
            telegram_processes[profile_id] = multiprocessing.Process(
                target=telegram_bot_process,
                args=(telegram_queues[profile_id], profile_id),
            )
            telegram_processes[profile_id].start()
        elif not telegram_should_run and telegram_is_running:
            logger.info(f"Stopping telegram bot process for profile '{profile_name}' (id={profile_id})")
            telegram_processes[profile_id].terminate()
            telegram_processes[profile_id].join()
            telegram_processes[profile_id] = None

        ### RSS ###
        rss_should_run = profile_settings.get("rss_process_running") == "True"
        rss_is_running = (
            profile_id in rss_processes
            and rss_processes[profile_id] is not None
            and rss_processes[profile_id].is_alive()
        )

        # Ensure queue exists for this profile
        if profile_id not in rss_queues:
            rss_queues[profile_id] = queue_manager.Queue()

        if rss_should_run and not rss_is_running:
            logger.info(f"Starting RSS process for profile '{profile_name}' (id={profile_id})")
            rss_processes[profile_id] = multiprocessing.Process(
                target=rss_feed_process,
                args=(rss_queues[profile_id], profile_id),
            )
            rss_processes[profile_id].start()
        elif not rss_should_run and rss_is_running:
            logger.info(f"Stopping RSS process for profile '{profile_name}' (id={profile_id})")
            rss_processes[profile_id].terminate()
            rss_processes[profile_id].join()
            rss_processes[profile_id] = None


def plugin_checker():
    # For each profile, reset process status at startup
    profiles = db.get_profiles()
    for profile_id, profile_name in profiles:
        telegram_enabled = db.get_profile_setting(profile_id, "telegram_enabled")
        logger.info(f"Profile '{profile_name}': Telegram enabled: {telegram_enabled}")
        rss_enabled = db.get_profile_setting(profile_id, "rss_enabled")
        logger.info(f"Profile '{profile_name}': RSS enabled: {rss_enabled}")

        # Reset process status at startup
        db.set_profile_setting(profile_id, "telegram_process_running", telegram_enabled)
        db.set_profile_setting(profile_id, "rss_process_running", rss_enabled)


if __name__ == "__main__":
    # Run db migrations
    current_version = db.get_parameter("version")
    if current_version is None:
        logger.warning(
            "Database version is missing; skipping migrations until version metadata is available."
        )
    # Check if there is a file that starts with the current version in the migrations folder. We keep comparing until
    # we find no migration files that start with the current version.
    migration_files = [f for f in os.listdir("migrations")]
    while current_version is not None:
        migration_file = next(
            (f for f in migration_files if f.startswith(current_version)), None
        )
        if not migration_file:
            break

        logger.info(f"Running migration: {migration_file}")
        db.create_or_update_sqlite_db("./migrations/" + migration_file)
        # Increment the version
        current_version = db.get_parameter("version")

    # Plugin checker
    plugin_checker()

    # Create shared queues
    items_queue = multiprocessing.Queue()
    new_items_queue = multiprocessing.Queue()

    # Create per-profile queues using multiprocessing.Manager for sharing between processes
    # Manager queues (manager.Queue()) produce proxy objects that can be pickled and shared
    # through managed dicts, unlike regular multiprocessing.Queue() objects
    manager = multiprocessing.Manager()
    telegram_queues = manager.dict()
    rss_queues = manager.dict()

    # Initialize queues for existing profiles
    profiles = db.get_profiles()
    for profile_id, profile_name in profiles:
        telegram_queues[profile_id] = manager.Queue()
        rss_queues[profile_id] = manager.Queue()

    # 1. Create and start the scrape process
    # This process will scrape items and put them in the items_queue
    current_query_refresh_delay = int(db.get_parameter("query_refresh_delay"))
    scrape_process = multiprocessing.Process(
        target=scraper_process, args=(items_queue,)
    )
    scrape_process.start()

    # 2. Create the item extractor process
    # This process will extract items from the items_queue and put them in the new_items_queue
    item_extractor_process = multiprocessing.Process(
        target=item_extractor, args=(items_queue, new_items_queue)
    )
    item_extractor_process.start()

    # 3. Create the dispatcher process
    # This process will handle the new items and send them to the enabled services per profile
    dispatcher_process = multiprocessing.Process(
        target=dispatcher_function,
        args=(
            new_items_queue,
            telegram_queues,
            rss_queues,
        ),
    )
    dispatcher_process.start()

    # 4. Set up a scheduler to monitor processes
    # This will check the process status in the database and start/stop processes as needed
    monitor_scheduler = BackgroundScheduler()
    monitor_scheduler.add_job(
        monitor_processes,
        "interval",
        seconds=5,
        args=[items_queue, telegram_queues, rss_queues, manager],
        name="process_monitor",
    )
    monitor_scheduler.start()

    # 5. Create and start the Web UI process
    # This process will provide a web interface to control the application
    web_ui_process_instance = multiprocessing.Process(target=web_ui_process)
    web_ui_process_instance.start()

    try:
        # Wait for processes to finish (which they won't unless interrupted)
        scrape_process.join()
        item_extractor_process.join()
        dispatcher_process.join()
        web_ui_process_instance.join()

        # plugins
        for pid, proc in telegram_processes.items():
            if proc:
                proc.join()
        for pid, proc in rss_processes.items():
            if proc:
                proc.join()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        logger.info("Main process interrupted")

        # Shutdown the monitor scheduler
        monitor_scheduler.shutdown()

        # Terminate all processes
        scrape_process.terminate()
        item_extractor_process.terminate()
        dispatcher_process.terminate()
        # Terminate web UI process
        web_ui_process_instance.terminate()

        # Plugins - per profile
        for pid, proc in telegram_processes.items():
            if proc and proc.is_alive():
                proc.terminate()
                db.set_profile_setting(pid, "telegram_process_running", "False")
        for pid, proc in rss_processes.items():
            if proc and proc.is_alive():
                proc.terminate()
                db.set_profile_setting(pid, "rss_process_running", "False")

        # Wait for all processes to terminate
        scrape_process.join()
        item_extractor_process.join()
        dispatcher_process.join()
        web_ui_process_instance.join()

        # Plugins
        for pid, proc in telegram_processes.items():
            if proc:
                proc.join()
        for pid, proc in rss_processes.items():
            if proc:
                proc.join()

        logger.info("All processes terminated")
