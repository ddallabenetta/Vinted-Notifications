from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

import db
from logger import get_logger
from pyVintedVN import Vinted, requester

# Get logger for this module
logger = get_logger(__name__)


def process_query(query, name=None, profile_id=1):
    """
    Process a Vinted query URL and add it to the database for a specific profile.

    Args:
        query (str): The Vinted query URL
        name (str, optional): A name for the query.
        profile_id (int): The profile ID to associate the query with.

    Returns:
        tuple: (message, is_new_query)
    """
    # Check if the URL is a brand URL (format: url/brand/id-name)
    parsed_url = urlparse(query)
    path_parts = parsed_url.path.strip("/").split("/")

    if len(path_parts) >= 2 and path_parts[0] == "brand":
        # Extract the brand ID from the format "id-name"
        brand_id_with_name = path_parts[1]
        brand_id = brand_id_with_name.split("-")[0]

        # Create a new URL with the standard format
        new_path = "/catalog"
        new_query_params = {"brand_ids[]": [brand_id]}
        new_query_string = urlencode(new_query_params, doseq=True)

        # Rebuild the URL
        query = urlunparse(
            (parsed_url.scheme, parsed_url.netloc, new_path, "", new_query_string, "")
        )
        logger.info(f"Converted brand URL to standard format: {query}")

        # Parse the URL and extract the query parameters
        parsed_url = urlparse(query)

    query_params = parse_qs(parsed_url.query)

    # Ensure the order flag is set to newest_first
    query_params["order"] = ["newest_first"]
    # Remove time and search_id if provided
    query_params.pop("time", None)
    query_params.pop("search_id", None)
    query_params.pop("disabled_personalization", None)
    query_params.pop("page", None)

    # Rebuild the query string and the entire URL
    new_query = urlencode(query_params, doseq=True)
    processed_query = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment,
        )
    )

    # Check if the query already exists in the same profile
    if db.is_query_in_db(processed_query, profile_id=profile_id) is True:
        return "Query already exists.", False
    else:
        # add the query to the db
        db.add_query_to_db(processed_query, name, profile_id=profile_id)
        return "Query added.", True


def get_formatted_query_list(profile_id=None):
    """
    Get a formatted list of all queries in the database.

    Args:
        profile_id (int, optional): If provided, only return queries for this profile.

    Returns:
        str: A formatted string with all queries, numbered
    """
    all_queries = db.get_queries(profile_id=profile_id)
    queries_keywords = []
    for query in all_queries:
        parsed_url = urlparse(query[1])
        query_params = parse_qs(parsed_url.query)

        # Get the name or Extract the value of 'search_text'
        query_name = (
            query[3]
            if query[3] is not None
            else query_params.get("search_text", [None])[0]
        )

        if query_name[0] is None:
            # Use query text instead of the whole query object
            queries_keywords.append([query[1]])
        else:
            queries_keywords.append(query_name)

    query_list = ("\n").join(
        [str(i + 1) + ". " + j for i, j in enumerate(queries_keywords)]
    )
    return query_list


def process_remove_query(number, profile_id=None):
    """
    Process the removal of a query from the database.

    Args:
        number (str): The number of the query to remove or "all" to remove all queries
        profile_id (int, optional): The profile ID for removing all queries.

    Returns:
        tuple: (message, success)
    """
    if number == "all":
        db.remove_all_queries_from_db(profile_id=profile_id)
        return "All queries removed.", True

    # Check if number is a valid digit
    if number.isdigit():
        # Remove the query from the database
        db.remove_query_from_db(number)
        return "Query removed.", True
    else:
        return "Invalid number.", False


def process_update_query(query_id, query, name):
    """
    Process the update of a query in the database.

    Args:
        query_id (int): The ID of the query to update
        query (str): The new Vinted query URL
        name (str, optional): A new name for the query.

    Returns:
        tuple: (message, success)
    """
    # Parse the URL and extract the query parameters
    parsed_url = urlparse(query)
    query_params = parse_qs(parsed_url.query)

    # Ensure the order flag is set to newest_first
    query_params["order"] = ["newest_first"]
    # Remove time and search_id if provided
    query_params.pop("time", None)
    query_params.pop("search_id", None)
    query_params.pop("disabled_personalization", None)
    query_params.pop("page", None)

    # Rebuild the query string and the entire URL
    new_query = urlencode(query_params, doseq=True)
    processed_query = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment,
        )
    )

    # Update the query in the database
    if db.update_query_in_db(query_id, processed_query, name):
        return "Query updated.", True
    else:
        return "Failed to update query.", False


def process_add_country(country, profile_id=1):
    """
    Process the addition of a country to the allowlist.

    Args:
        country (str): The country code to add
        profile_id (int): The profile ID.

    Returns:
        tuple: (message, country_list)
    """
    # Format the country code (remove spaces)
    country = country.replace(" ", "")
    country_list = db.get_allowlist(profile_id=profile_id)

    # Validate the country code (check if it's 2 characters long)
    if len(country) != 2:
        return "Invalid country code", country_list

    # Check if the country is already in the allowlist
    if country_list != 0 and country.upper() in country_list:
        return f'Country "{country.upper()}" already in allowlist.', country_list

    # Add the country to the allowlist
    db.add_to_allowlist(country.upper(), profile_id=profile_id)
    return "Country added.", db.get_allowlist(profile_id=profile_id)


def process_remove_country(country, profile_id=1):
    """
    Process the removal of a country from the allowlist.

    Args:
        country (str): The country code to remove
        profile_id (int): The profile ID.

    Returns:
        tuple: (message, country_list)
    """
    # Format the country code (remove spaces)
    country = country.replace(" ", "")

    # Validate the country code (check if it's 2 characters long)
    if len(country) != 2:
        return "Invalid country code", db.get_allowlist(profile_id=profile_id)

    # Remove the country from the allowlist
    db.remove_from_allowlist(country.upper(), profile_id=profile_id)
    return "Country removed.", db.get_allowlist(profile_id=profile_id)


def process_add_blocked_user(username, profile_id=1):
    """
    Process the addition of a user to the blocked users list.

    Args:
        username (str): The Vinted username to block
        profile_id (int): The profile ID.

    Returns:
        tuple: (message, success)
    """
    username = username.strip()

    if not username:
        return "Invalid username.", False

    if db.is_user_blocked(username, profile_id=profile_id):
        return f'User "{username}" is already blocked.', False

    db.add_blocked_user(username, profile_id=profile_id)
    return "User blocked.", True


def process_remove_blocked_user(username, profile_id=1):
    """
    Process the removal of a user from the blocked users list.

    Args:
        username (str): The Vinted username to unblock
        profile_id (int): The profile ID.

    Returns:
        tuple: (message, success)
    """
    username = username.strip()

    if not username:
        return "Invalid username.", False

    db.remove_blocked_user(username, profile_id=profile_id)
    return "User unblocked.", True


def get_user_country(profile_id):
    """
    Get the country code for a Vinted user.

    Args:
        profile_id (str): The Vinted user's profile ID

    Returns:
        str: The user's country code (2-letter ISO code) or "XX" if it can't be determined
    """
    # Users are shared between all Vinted platforms, so we can use whatever locale we want
    url = f"https://www.vinted.fr/api/v2/users/{profile_id}?localize=false"
    response = requester.get(url)
    # That's a LOT of requests, so if we get a 429 we wait a bit before retrying once
    if response.status_code == 429:
        # In case of rate limit, we're switching the endpoint. This one is slower, but it doesn't RL as soon.
        # We're limiting the items per page to 1 to grab as little data as possible
        url = f"https://www.vinted.fr/api/v2/users/{profile_id}/items?page=1&per_page=1"
        response = requester.get(url)
        try:
            user_country = response.json()["items"][0]["user"]["country_iso_code"]
        except KeyError:
            logger.warning(
                "Couldn't get the country due to too many requests. Returning default value."
            )
            user_country = "XX"
    else:
        user_country = response.json()["user"]["country_iso_code"]
    return user_country


def process_items(queue):
    """
    Process all queries from the database, search for items, and put them in the queue.
    Each item in the queue includes the profile_id for routing.

    Args:
        queue (Queue): The queue to put the items in.

    Returns:
        None
    """

    all_queries = db.get_queries()

    # Initialize Vinted
    vinted = Vinted()

    # for each keyword we parse data
    for query in all_queries:
        query_id = query[0]
        query_url = query[1]
        profile_id = query[4]

        # Get items_per_query from the profile settings
        items_per_query = int(db.get_profile_setting(profile_id, "items_per_query") or "20")

        all_items = vinted.items.search(query_url, nbr_items=items_per_query)
        # Filter to only include new items. This should reduce the amount of db calls.
        data = [item for item in all_items if item.is_new_item()]
        queue.put((data, query_id, profile_id))
        logger.info(f"Scraped {len(data)} items for query: {query_url}")


def clear_item_queue(items_queue, new_items_queue):
    """
    Process items from the items_queue.
    This function is scheduled to run frequently.
    """
    if not items_queue.empty():
        data, query_id, profile_id = items_queue.get()
        banwords_str = db.get_profile_setting(profile_id, "banwords")
        for item in reversed(data):
            # If already in db, pass
            last_query_timestamp = db.get_last_timestamp(query_id)
            if (
                last_query_timestamp is not None
                and last_query_timestamp >= item.raw_timestamp
            ):
                pass
            # In case of multiple queries, we need to check if the item is already in the db
            elif db.is_item_in_db_by_id(item.id) is True:
                # We update the timestamp
                db.update_last_timestamp(query_id, item.raw_timestamp)
                pass
            # Check if the user is blocked (per-profile)
            elif db.is_user_blocked(item.raw_data["user"]["login"], profile_id=profile_id):
                db.update_last_timestamp(query_id, item.raw_timestamp)
                pass
            # If there's an allowlist and
            # If the user's country is not in the allowlist, we just update the timestamp
            elif db.get_allowlist(profile_id=profile_id) != 0 and (
                get_user_country(item.raw_data["user"]["id"])
            ) not in (db.get_allowlist(profile_id=profile_id) + ["XX"]):
                db.update_last_timestamp(query_id, item.raw_timestamp)
                pass
            # Check if the item title contains any banwords (per-profile)
            elif banwords_str and contains_banwords(item.title, banwords_str):
                # If it contains banwords, just update the timestamp and skip
                db.update_last_timestamp(query_id, item.raw_timestamp)
                pass
            else:
                # We create the message using the profile's template
                message_template = db.get_profile_setting(profile_id, "message_template")
                if not message_template:
                    message_template = "{title}\n{price}\n{brand}"
                content = message_template.format(
                    title=item.title,
                    price=str(item.price) + " " + item.currency,
                    brand=item.brand_title,
                    image=None if item.photo is None else item.photo,
                )
                # add the item to the queue with profile_id
                new_items_queue.put((content, item.url, "Open Vinted", None, None, profile_id))
                # Add the item to the db
                db.add_item_to_db(
                    id=item.id,
                    timestamp=item.raw_timestamp,
                    price=item.price,
                    title=item.title,
                    photo_url=item.photo,
                    query_id=query_id,
                    currency=item.currency,
                    username=item.raw_data.get("user", {}).get("login"),
                )


def contains_banwords(title, banwords_str):
    """
    Check if a title contains any banwords.

    Args:
        title (str): The title to check
        banwords_str (str): List of banwords separated by 3 pipe character
    Returns:
        bool: True if the title contains any banwords, False otherwise
    """

    # Split the banwords string into a list using pipe as delimiter
    banwords = [
        word.strip().lower() for word in banwords_str.split("|||") if word.strip()
    ]

    # If the list is empty, return False
    if not banwords:
        return False

    # Check if any banword is in the title (case-insensitive)
    title_lower = title.lower()
    for word in banwords:
        if word in title_lower:
            return True

    return False


def check_version():
    """
    Check if the application is up to date
    """
    try:
        # Get URL from the database
        github_url = db.get_parameter("github_url")
        # Get version from the database
        ver = db.get_parameter("version")
        # Get latest version from the repository
        url = f"{github_url}/releases/latest"
        response = requests.get(url)

        if response.status_code == 200:
            latest_version = response.url.split("/")[-1]
            is_up_to_date = ver == latest_version
            return is_up_to_date, ver, latest_version, github_url
        else:
            # If we can't check, assume it's up to date
            return True, ver, ver, github_url
    except Exception as e:
        logger.error(f"Error checking for new version: {str(e)}", exc_info=True)
        # If we can't check, assume it's up to date
        return True, ver, ver, github_url
