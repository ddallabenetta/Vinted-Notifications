import sqlite3
from datetime import datetime, timezone
from traceback import print_exc

DB_PATH = "./data/vinted_notifications.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_or_update_sqlite_db(db_path):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Using the sql script
        with open(db_path, "r", encoding="utf-8") as sql_file:
            sql_script = sql_file.read()
            cursor.executescript(sql_script)

        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def table_exists(table_name):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return cursor.fetchone() is not None
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


# ==================== Profile Functions ====================


def get_profiles():
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM profiles ORDER BY id")
        return cursor.fetchall()
    except Exception:
        print_exc()
        return []
    finally:
        if conn:
            conn.close()


def get_profile(profile_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE id=?", (profile_id,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def get_all_profile_settings(profile_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE id=?", (profile_id,))
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return {}
    except Exception:
        print_exc()
        return {}
    finally:
        if conn:
            conn.close()


def create_profile(name):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO profiles (name) VALUES (?)", (name,))
        conn.commit()
        return cursor.lastrowid
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def update_profile_name(profile_id, name):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET name=? WHERE id=?", (name, profile_id))
        conn.commit()
        return True
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


def delete_profile(profile_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Delete items linked to this profile's queries
        cursor.execute(
            "DELETE FROM items WHERE query_id IN (SELECT id FROM queries WHERE profile_id=?)",
            (profile_id,),
        )
        # Delete queries
        cursor.execute("DELETE FROM queries WHERE profile_id=?", (profile_id,))
        # Delete allowlist entries
        cursor.execute("DELETE FROM allowlist WHERE profile_id=?", (profile_id,))
        # Delete blocked users
        cursor.execute("DELETE FROM blocked_users WHERE profile_id=?", (profile_id,))
        # Delete the profile
        cursor.execute("DELETE FROM profiles WHERE id=?", (profile_id,))
        conn.commit()
        return True
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


def get_profile_setting(profile_id, key):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT {key} FROM profiles WHERE id=?", (profile_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def set_profile_setting(profile_id, key, value):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE profiles SET {key}=? WHERE id=?", (value, profile_id)
        )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def update_profile_settings(profile_id, settings):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for key, value in settings.items():
            cursor.execute(
                f"UPDATE profiles SET {key}=? WHERE id=?", (value, profile_id)
            )
        conn.commit()
        return True
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


# ==================== Item Functions ====================


def is_item_in_db_by_id(id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT() FROM items WHERE item=?", (id,))
        if cursor.fetchone()[0]:
            return True
        return False
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_last_timestamp(query_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT last_item FROM queries WHERE id=?", (query_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def update_last_timestamp(query_id, timestamp):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE queries SET last_item=? WHERE id=?", (timestamp, query_id)
        )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def add_item_to_db(id, title, query_id, price, timestamp, photo_url, currency="EUR", username=None):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Insert into db the id and the query_id related to the item
        cursor.execute(
            "INSERT INTO items (item, title, price, currency, timestamp, photo_url, query_id, username) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (id, title, price, currency, timestamp, photo_url, query_id, username),
        )
        # Update the last item for the query
        cursor.execute(
            "UPDATE queries SET last_item=? WHERE id=?", (timestamp, query_id)
        )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


# ==================== Query Functions ====================


def get_queries(profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if profile_id is not None:
            cursor.execute(
                "SELECT id, query, last_item, query_name, profile_id FROM queries WHERE profile_id=?",
                (profile_id,),
            )
        else:
            cursor.execute("SELECT id, query, last_item, query_name, profile_id FROM queries")
        return cursor.fetchall()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def is_query_in_db(processed_query, profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if profile_id is not None:
            cursor.execute(
                "SELECT COUNT() FROM queries WHERE query = ? AND profile_id = ?",
                (processed_query, profile_id),
            )
        else:
            cursor.execute(
                "SELECT COUNT() FROM queries WHERE query = ?", (processed_query,)
            )
        if cursor.fetchone()[0]:
            return True
        return False
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


def add_query_to_db(query, name=None, profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if name:
            cursor.execute(
                "INSERT INTO queries (query, last_item, query_name, profile_id) VALUES (?, NULL, ?, ?)",
                (query, name, profile_id),
            )
        else:
            cursor.execute(
                "INSERT INTO queries (query, last_item, profile_id) VALUES (?, NULL, ?)",
                (query, profile_id),
            )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_query_id_by_rowid(rowid):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = f"SELECT id FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY ROWID) rn FROM queries) t WHERE rn={rowid}"
        cursor.execute(query)
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def get_profile_id_for_query(query_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT profile_id FROM queries WHERE id=?", (query_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def remove_query_from_db(query_number):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Delete items associated with this query using query_id
        cursor.execute("DELETE FROM items WHERE query_id=?", (query_number,))
        # Delete the query
        cursor.execute("DELETE FROM queries WHERE id=?", (query_number,))
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def remove_all_queries_from_db(profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if profile_id is not None:
            # Delete items for queries in this profile
            cursor.execute(
                "DELETE FROM items WHERE query_id IN (SELECT id FROM queries WHERE profile_id=?)",
                (profile_id,),
            )
            cursor.execute("DELETE FROM queries WHERE profile_id=?", (profile_id,))
        else:
            cursor.execute("DELETE FROM items")
            cursor.execute("DELETE FROM queries")
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def update_query_in_db(query_id, query, name):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE queries SET query=?, query_name=? WHERE id=?",
            (query, name, query_id),
        )
        conn.commit()
        return True
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


# ==================== Allowlist Functions ====================


def add_to_allowlist(country, profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO allowlist (country, profile_id) VALUES (?, ?)",
            (country, profile_id),
        )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def remove_from_allowlist(country, profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM allowlist WHERE country=? AND profile_id=?",
            (country, profile_id),
        )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_allowlist(profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT country FROM allowlist WHERE profile_id=?", (profile_id,)
        )
        countries = [country[0] for country in cursor.fetchall()]
        if not countries:
            return 0
        return countries
    finally:
        if conn:
            conn.close()


def clear_allowlist(profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM allowlist WHERE profile_id=?", (profile_id,))
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


# ==================== Blocked Users Functions ====================


def add_blocked_user(username, profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO blocked_users (username, profile_id) VALUES (?, ?)",
            (username, profile_id),
        )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def remove_blocked_user(username, profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM blocked_users WHERE username=? AND profile_id=?",
            (username, profile_id),
        )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_blocked_users(profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username FROM blocked_users WHERE profile_id=?", (profile_id,)
        )
        users = [row[0] for row in cursor.fetchall()]
        if not users:
            return 0
        return users
    finally:
        if conn:
            conn.close()


def is_user_blocked(username, profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if profile_id is not None:
            cursor.execute(
                "SELECT 1 FROM blocked_users WHERE username=? AND profile_id=?",
                (username, profile_id),
            )
        else:
            cursor.execute("SELECT 1 FROM blocked_users WHERE username=?", (username,))
        return cursor.fetchone() is not None
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


def clear_blocked_users(profile_id=1):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM blocked_users WHERE profile_id=?", (profile_id,)
        )
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


# ==================== Global Parameter Functions ====================


def get_parameter(key):
    conn = None
    try:
        if not table_exists("parameters"):
            return None
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM parameters WHERE key=?", (key,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def set_parameter(key, value):
    conn = None
    try:
        if not table_exists("parameters"):
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE parameters SET value=? WHERE key=?", (value, key))
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_all_parameters():
    conn = None
    try:
        if not table_exists("parameters"):
            return {}
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM parameters")
        return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception:
        print_exc()
        return {}
    finally:
        if conn:
            conn.close()


# ==================== Items Query Functions ====================


def get_items(limit=50, query=None, profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if query:
            cursor.execute("SELECT id FROM queries WHERE query=?", (query,))
            result = cursor.fetchone()
            if result:
                query_id = result[0]
                cursor.execute(
                    "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url, q.query_name, i.username FROM items i JOIN queries q ON i.query_id = q.id WHERE i.query_id=? ORDER BY i.timestamp DESC LIMIT ?",
                    (query_id, limit),
                )
            else:
                return []
        elif profile_id is not None:
            cursor.execute(
                "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url, q.query_name, i.username FROM items i JOIN queries q ON i.query_id = q.id WHERE q.profile_id=? ORDER BY i.timestamp DESC LIMIT ?",
                (profile_id, limit),
            )
        else:
            cursor.execute(
                "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url, q.query_name, i.username FROM items i JOIN queries q ON i.query_id = q.id ORDER BY i.timestamp DESC LIMIT ?",
                (limit,),
            )
        return cursor.fetchall()
    except Exception:
        print_exc()
        return []
    finally:
        if conn:
            conn.close()


def get_total_items_count(profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if profile_id is not None:
            cursor.execute(
                "SELECT COUNT(*) FROM items i JOIN queries q ON i.query_id = q.id WHERE q.profile_id=?",
                (profile_id,),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM items")
        return cursor.fetchone()[0]
    except Exception:
        print_exc()
        return 0
    finally:
        if conn:
            conn.close()


def get_total_queries_count(profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if profile_id is not None:
            cursor.execute(
                "SELECT COUNT(*) FROM queries WHERE profile_id=?", (profile_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM queries")
        return cursor.fetchone()[0]
    except Exception:
        print_exc()
        return 0
    finally:
        if conn:
            conn.close()


def get_last_found_item(profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if profile_id is not None:
            cursor.execute(
                "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url, i.username FROM items i JOIN queries q ON i.query_id = q.id WHERE q.profile_id=? ORDER BY i.timestamp DESC LIMIT 1",
                (profile_id,),
            )
        else:
            cursor.execute(
                "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url, i.username FROM items i JOIN queries q ON i.query_id = q.id ORDER BY i.timestamp DESC LIMIT 1"
            )
        return cursor.fetchone()
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def get_items_per_day(profile_id=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if profile_id is not None:
            cursor.execute(
                "SELECT COUNT(*) FROM items i JOIN queries q ON i.query_id = q.id WHERE q.profile_id=?",
                (profile_id,),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM items")
        total_items = cursor.fetchone()[0]

        if total_items == 0:
            return 0

        if profile_id is not None:
            cursor.execute(
                "SELECT MIN(i.timestamp), MAX(i.timestamp) FROM items i JOIN queries q ON i.query_id = q.id WHERE q.profile_id=?",
                (profile_id,),
            )
        else:
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM items")
        min_timestamp, max_timestamp = cursor.fetchone()

        min_date = datetime.fromtimestamp(min_timestamp, tz=timezone.utc).date()
        max_date = datetime.fromtimestamp(max_timestamp, tz=timezone.utc).date()
        days_diff = (max_date - min_date).days + 1

        days_diff = max(1, days_diff)

        return round(total_items / days_diff, 1)
    except Exception:
        print_exc()
        return 0
    finally:
        if conn:
            conn.close()
