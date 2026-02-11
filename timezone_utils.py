"""
Timezone utility functions for consistent timestamp handling across the application.
All timestamps in the database are stored as UTC Unix timestamps.
This module provides functions to convert them to the configured local timezone.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import db
from logger import get_logger

logger = get_logger(__name__)


def get_local_timezone():
    """
    Get the configured local timezone from the database.

    Returns:
        ZoneInfo: The configured timezone object, defaults to Europe/Rome if not set
    """
    try:
        tz_string = db.get_parameter("timezone")
        if tz_string:
            return ZoneInfo(tz_string)
    except Exception as e:
        logger.warning(f"Error getting timezone from database: {e}")

    # Default to Europe/Rome
    return ZoneInfo("Europe/Rome")


def utc_timestamp_to_local(timestamp):
    """
    Convert a UTC Unix timestamp to a datetime object in the configured local timezone.

    Args:
        timestamp (int|float): Unix timestamp in UTC

    Returns:
        datetime: Datetime object in the configured local timezone
    """
    try:
        # Create UTC datetime from timestamp
        utc_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        # Convert to local timezone
        local_tz = get_local_timezone()
        return utc_dt.astimezone(local_tz)
    except Exception as e:
        logger.error(f"Error converting timestamp {timestamp} to local time: {e}")
        # Fallback to naive datetime
        return datetime.fromtimestamp(timestamp)


def format_local_timestamp(timestamp, format_string="%Y-%m-%d %H:%M:%S"):
    """
    Format a UTC Unix timestamp as a string in the configured local timezone.

    Args:
        timestamp (int|float): Unix timestamp in UTC
        format_string (str): strftime format string, defaults to "%Y-%m-%d %H:%M:%S"

    Returns:
        str: Formatted datetime string in local timezone
    """
    local_dt = utc_timestamp_to_local(timestamp)
    return local_dt.strftime(format_string)


def local_now():
    """
    Get the current datetime in the configured local timezone.

    Returns:
        datetime: Current datetime in local timezone
    """
    local_tz = get_local_timezone()
    return datetime.now(local_tz)


def parse_time_string(time_string):
    """
    Parse a time string (HH:MM) and return a time object in the local timezone.
    This is used for schedule_start_time and schedule_end_time.

    Args:
        time_string (str): Time in format "HH:MM"

    Returns:
        datetime.time: Time object
    """
    return datetime.strptime(time_string, "%H:%M").time()
