import os
import sys
import signal
from urllib.parse import parse_qs, urlparse
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

# Add parent directory to the path so we can import the core module
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import core
import db
import timezone_utils
from logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)


def get_current_profile_id():
    """Get the current profile ID from session, defaulting to first available profile."""
    profile_id = session.get("profile_id")
    if profile_id is not None:
        # Verify profile still exists
        profile = db.get_profile(profile_id)
        if profile:
            return profile_id
    # Default to first profile
    profiles = db.get_profiles()
    if profiles:
        session["profile_id"] = profiles[0][0]
        return profiles[0][0]
    return 1


@app.context_processor
def inject_profiles():
    """Inject profiles list and current profile into all templates."""
    profiles = db.get_profiles()
    current_profile_id = get_current_profile_id()
    current_profile = db.get_profile(current_profile_id)
    return dict(
        profiles=profiles,
        current_profile_id=current_profile_id,
        current_profile=current_profile,
    )


# ==================== Profile Routes ====================


@app.route("/switch_profile/<int:profile_id>")
def switch_profile(profile_id):
    profile = db.get_profile(profile_id)
    if profile:
        session["profile_id"] = profile_id
    return redirect(request.referrer or url_for("index"))


@app.route("/create_profile", methods=["POST"])
def create_profile():
    name = request.form.get("profile_name", "").strip()
    if not name:
        flash("Profile name cannot be empty.", "danger")
        return redirect(url_for("config"))
    profile_id = db.create_profile(name)
    if profile_id:
        flash(f'Profile "{name}" created.', "success")
        session["profile_id"] = profile_id
    else:
        flash("Failed to create profile.", "danger")
    return redirect(url_for("config"))


@app.route("/rename_profile", methods=["POST"])
def rename_profile():
    profile_id = get_current_profile_id()
    name = request.form.get("profile_name", "").strip()
    if not name:
        flash("Profile name cannot be empty.", "danger")
        return redirect(url_for("config"))
    if db.update_profile_name(profile_id, name):
        flash(f'Profile renamed to "{name}".', "success")
    else:
        flash("Failed to rename profile.", "danger")
    return redirect(url_for("config"))


@app.route("/delete_profile/<int:profile_id>", methods=["POST"])
def delete_profile(profile_id):
    profiles = db.get_profiles()
    if len(profiles) <= 1:
        flash("Cannot delete the last profile.", "danger")
        return redirect(url_for("config"))

    profile = db.get_profile(profile_id)
    if not profile:
        flash("Profile not found.", "danger")
        return redirect(url_for("config"))

    name = profile["name"]
    if db.delete_profile(profile_id):
        flash(f'Profile "{name}" deleted.', "success")
        # Switch to another profile
        if session.get("profile_id") == profile_id:
            remaining = db.get_profiles()
            if remaining:
                session["profile_id"] = remaining[0][0]
    else:
        flash("Failed to delete profile.", "danger")
    return redirect(url_for("config"))


# ==================== Dashboard ====================


@app.route("/")
def index():
    profile_id = get_current_profile_id()

    try:
        # Fetch stats scoped to the current profile
        total_queries = db.get_total_queries_count(profile_id=profile_id)
        total_items = db.get_total_items_count(profile_id=profile_id)
        items_per_day = db.get_items_per_day(profile_id=profile_id)

        # Get recent items for the current profile
        recent_items_raw = db.get_items(limit=10, profile_id=profile_id)
        recent_items = []
        for item in recent_items_raw:
            item_id, title, price, currency, timestamp, query, photo_url, query_name, username = item
            display_query = query_name if query_name else query
            # Format time
            formatted_time = timezone_utils.format_timestamp(timestamp)

            recent_items.append({
                "item": item_id,
                "title": title,
                "price": price,
                "currency": currency,
                "timestamp": formatted_time,
                "query": display_query,
                "photo_url": photo_url,
                "url": f"https://www.vinted.fr/items/{item_id}",
                "username": username,
                "is_blocked": db.is_user_blocked(username, profile_id=profile_id) if username else False,
            })

        # Check version
        try:
            is_up_to_date, ver, latest_version, github_url = core.check_version()
        except Exception:
            is_up_to_date, ver, latest_version, github_url = True, "?", "?", "#"

        return render_template(
            "index.html",
            total_queries=total_queries,
            total_items=total_items,
            items_per_day=items_per_day,
            recent_items=recent_items,
            is_up_to_date=is_up_to_date,
            ver=ver,
            latest_version=latest_version,
            github_url=github_url,
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}", exc_info=True)
        return render_template(
            "index.html",
            total_queries=0,
            total_items=0,
            items_per_day=0,
            recent_items=[],
            is_up_to_date=True,
            ver="?",
            latest_version="?",
            github_url="#",
        )


# ==================== Queries ====================


@app.route("/queries")
def queries():
    profile_id = get_current_profile_id()
    all_queries = db.get_queries(profile_id=profile_id)
    queries_list = []
    for query in all_queries:
        query_id, query_url, last_item, query_name, p_id = query
        parsed_url = urlparse(query_url)
        query_params = parse_qs(parsed_url.query)
        search_text = query_params.get("search_text", [None])[0]
        display = query_name if query_name else (search_text if search_text else query_url)
        queries_list.append({
            "id": query_id,
            "query": query_url,
            "query_name": query_name,
            "display": display,
            "last_item": last_item,
        })

    return render_template("queries.html", queries=queries_list)


@app.route("/add_query", methods=["POST"])
def add_query():
    profile_id = get_current_profile_id()
    query = request.form.get("query", "")
    name = request.form.get("query_name", "").strip() or None

    if not query:
        flash("No query provided.", "danger")
        return redirect(url_for("queries"))

    message, is_new = core.process_query(query, name, profile_id=profile_id)
    flash(message, "success" if is_new else "warning")
    return redirect(url_for("queries"))


@app.route("/remove_query/<int:query_id>", methods=["POST"])
def remove_query(query_id):
    db.remove_query_from_db(query_id)
    flash("Query removed.", "success")
    return redirect(url_for("queries"))


@app.route("/update_query/<int:query_id>", methods=["POST"])
def update_query(query_id):
    query = request.form.get("query", "")
    name = request.form.get("query_name", "").strip() or None

    if not query:
        flash("No query provided.", "danger")
        return redirect(url_for("queries"))

    message, success = core.process_update_query(query_id, query, name)
    flash(message, "success" if success else "danger")
    return redirect(url_for("queries"))


# ==================== Items ====================


@app.route("/items")
def items():
    profile_id = get_current_profile_id()
    selected_query = request.args.get("query", "")
    limit = request.args.get("limit", "25")

    try:
        limit = int(limit)
    except ValueError:
        limit = 25

    # Get all queries for this profile (for the filter dropdown)
    all_queries = db.get_queries(profile_id=profile_id)
    queries_list = []
    for query in all_queries:
        query_id, query_url, last_item, query_name, p_id = query
        parsed_url = urlparse(query_url)
        query_params = parse_qs(parsed_url.query)
        search_text = query_params.get("search_text", [None])[0]
        display = query_name if query_name else (search_text if search_text else query_url)
        queries_list.append({
            "query_id": str(query_id),
            "display": display,
        })

    # Get items
    if selected_query:
        try:
            selected_query_id = int(selected_query)
            import sqlite3
            conn = None
            try:
                conn = sqlite3.connect(db.DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url, q.query_name, i.username FROM items i JOIN queries q ON i.query_id = q.id WHERE i.query_id=? AND q.profile_id=? ORDER BY i.timestamp DESC LIMIT ?",
                    (selected_query_id, profile_id, limit),
                )
                items_raw = cursor.fetchall()
            finally:
                if conn:
                    conn.close()
        except (ValueError, Exception):
            items_raw = db.get_items(limit=limit, profile_id=profile_id)
    else:
        items_raw = db.get_items(limit=limit, profile_id=profile_id)

    items_list = []
    for item in items_raw:
        item_id, title, price, currency, timestamp, query, photo_url, query_name, username = item
        display_query = query_name if query_name else query
        formatted_time = timezone_utils.format_timestamp(timestamp)

        items_list.append({
            "item": item_id,
            "title": title,
            "price": price,
            "currency": currency,
            "timestamp": formatted_time,
            "query": display_query,
            "photo_url": photo_url,
            "url": f"https://www.vinted.fr/items/{item_id}",
            "username": username,
            "is_blocked": db.is_user_blocked(username, profile_id=profile_id) if username else False,
        })

    # Find the display text for the selected query
    selected_query_display = ""
    for q in queries_list:
        if q["query_id"] == selected_query:
            selected_query_display = q["display"]
            break

    return render_template(
        "items.html",
        items=items_list,
        queries=queries_list,
        selected_query=selected_query,
        selected_query_display=selected_query_display,
        limit=limit,
    )


# ==================== Configuration ====================


@app.route("/config")
def config():
    profile_id = get_current_profile_id()

    # Get global parameters
    params = db.get_all_parameters()

    # Get per-profile settings
    profile_settings = db.get_all_profile_settings(profile_id)

    # Merge into a single dict for template compatibility
    merged = {}
    merged.update(params)
    merged.update(profile_settings)

    return render_template("config.html", params=merged)


@app.route("/update_config", methods=["POST"])
def update_config():
    profile_id = get_current_profile_id()

    # Per-profile settings
    profile_settings = {
        "telegram_enabled": "True" if request.form.get("telegram_enabled") else "False",
        "telegram_token": request.form.get("telegram_token", ""),
        "telegram_chat_id": request.form.get("telegram_chat_id", ""),
        "rss_enabled": "True" if request.form.get("rss_enabled") else "False",
        "rss_port": request.form.get("rss_port", "8080"),
        "rss_max_items": request.form.get("rss_max_items", "100"),
        "banwords": request.form.get("banwords", ""),
        "message_template": request.form.get("message_template", ""),
        "items_per_query": request.form.get("items_per_query", "20"),
    }
    db.update_profile_settings(profile_id, profile_settings)

    # Global settings
    global_params = {
        "query_refresh_delay": request.form.get("query_refresh_delay", "60"),
        "timezone": request.form.get("timezone", "Europe/Rome"),
        "schedule_enabled": "True" if request.form.get("schedule_enabled") else "False",
        "schedule_start_time": request.form.get("schedule_start_time", "08:00"),
        "schedule_end_time": request.form.get("schedule_end_time", "01:00"),
        "check_proxies": "True" if request.form.get("check_proxies") else "False",
        "proxy_list": request.form.get("proxy_list", ""),
        "proxy_list_link": request.form.get("proxy_list_link", ""),
        "user_agents": request.form.get("user_agents", "[]"),
        "default_headers": request.form.get("default_headers", "{}"),
    }
    for key, value in global_params.items():
        db.set_parameter(key, value)

    flash("Configuration saved.", "success")
    return redirect(url_for("config"))


# ==================== Process Control ====================


@app.route("/control/<process>/<action>", methods=["POST"])
def control_process(process, action):
    profile_id = get_current_profile_id()

    if process == "telegram":
        if action == "start":
            token = db.get_profile_setting(profile_id, "telegram_token")
            chat_id = db.get_profile_setting(profile_id, "telegram_chat_id")
            if not token or not chat_id:
                return jsonify({
                    "status": "warning",
                    "message": "Please configure Telegram token and chat ID first."
                })
            db.set_profile_setting(profile_id, "telegram_process_running", "True")
            return jsonify({"status": "success", "message": "Telegram bot starting..."})
        elif action == "stop":
            db.set_profile_setting(profile_id, "telegram_process_running", "False")
            return jsonify({"status": "success", "message": "Telegram bot stopping..."})
    elif process == "rss":
        if action == "start":
            db.set_profile_setting(profile_id, "rss_process_running", "True")
            return jsonify({"status": "success", "message": "RSS feed starting..."})
        elif action == "stop":
            db.set_profile_setting(profile_id, "rss_process_running", "False")
            return jsonify({"status": "success", "message": "RSS feed stopping..."})

    return jsonify({"status": "error", "message": "Invalid process or action."})


@app.route("/control/status")
def control_status():
    profile_id = get_current_profile_id()
    telegram_running = db.get_profile_setting(profile_id, "telegram_process_running") == "True"
    rss_running = db.get_profile_setting(profile_id, "rss_process_running") == "True"
    return jsonify({
        "telegram": telegram_running,
        "rss": rss_running,
    })


@app.route("/control/restart", methods=["POST"])
def control_restart():
    try:
        os.kill(os.getppid(), signal.SIGHUP)
        return jsonify({"status": "success", "message": "Service restarting..."})
    except Exception as e:
        logger.error(f"Error restarting service: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Error: {str(e)}"})


# ==================== Allowlist ====================


@app.route("/allowlist")
def allowlist():
    profile_id = get_current_profile_id()
    countries = db.get_allowlist(profile_id=profile_id)
    if countries == 0:
        countries = []
    return render_template("allowlist.html", countries=countries)


@app.route("/add_country", methods=["POST"])
def add_country():
    profile_id = get_current_profile_id()
    country = request.form.get("country", "")
    message, _ = core.process_add_country(country, profile_id=profile_id)
    flash(message, "success" if "added" in message.lower() else "warning")
    return redirect(url_for("allowlist"))


@app.route("/remove_country/<country>", methods=["POST"])
def remove_country(country):
    profile_id = get_current_profile_id()
    core.process_remove_country(country, profile_id=profile_id)
    flash("Country removed.", "success")
    return redirect(url_for("allowlist"))


@app.route("/clear_allowlist", methods=["POST"])
def clear_allowlist():
    profile_id = get_current_profile_id()
    db.clear_allowlist(profile_id=profile_id)
    flash("Allowlist cleared.", "success")
    return redirect(url_for("allowlist"))


# ==================== Blocked Users ====================


@app.route("/blocked_users")
def blocked_users():
    profile_id = get_current_profile_id()
    users = db.get_blocked_users(profile_id=profile_id)
    if users == 0:
        users = []
    return render_template("blocked_users.html", users=users)


@app.route("/add_blocked_user", methods=["POST"])
def add_blocked_user():
    profile_id = get_current_profile_id()
    username = request.form.get("username", "")
    message, success = core.process_add_blocked_user(username, profile_id=profile_id)
    flash(message, "success" if success else "warning")
    return redirect(url_for("blocked_users"))


@app.route("/remove_blocked_user/<username>", methods=["POST"])
def remove_blocked_user(username):
    profile_id = get_current_profile_id()
    core.process_remove_blocked_user(username, profile_id=profile_id)
    flash("User unblocked.", "success")
    return redirect(url_for("blocked_users"))


@app.route("/clear_blocked_users", methods=["POST"])
def clear_blocked_users():
    profile_id = get_current_profile_id()
    db.clear_blocked_users(profile_id=profile_id)
    flash("All blocked users cleared.", "success")
    return redirect(url_for("blocked_users"))


@app.route("/api/toggle_block_user", methods=["POST"])
def toggle_block_user():
    profile_id = get_current_profile_id()
    username = request.form.get("username", "").strip()
    if not username:
        return jsonify({"status": "error", "message": "No username provided."})

    if db.is_user_blocked(username, profile_id=profile_id):
        db.remove_blocked_user(username, profile_id=profile_id)
        return jsonify({
            "status": "success",
            "message": f'User "{username}" unblocked.',
            "blocked": False,
        })
    else:
        db.add_blocked_user(username, profile_id=profile_id)
        return jsonify({
            "status": "success",
            "message": f'User "{username}" blocked.',
            "blocked": True,
        })


@app.route("/api/blocked_users/search")
def search_blocked_users():
    profile_id = get_current_profile_id()
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify([])

    users = db.get_blocked_users(profile_id=profile_id)
    if users == 0:
        return jsonify([])

    matching = [u for u in users if query in u.lower()]
    return jsonify(matching[:10])


# ==================== Logs ====================


@app.route("/logs")
def logs():
    return render_template("logs.html")


@app.route("/api/logs")
def api_logs():
    try:
        log_file = os.path.join(os.path.dirname(__file__), "..", "logs", "vinted.log")
        if not os.path.exists(log_file):
            return jsonify({"logs": []})

        lines = request.args.get("lines", "100")
        try:
            lines = int(lines)
        except ValueError:
            lines = 100

        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            log_lines = all_lines[-lines:]

        return jsonify({"logs": log_lines})
    except Exception as e:
        logger.error(f"Error reading logs: {e}", exc_info=True)
        return jsonify({"logs": [], "error": str(e)})


# ==================== App Runner ====================


def web_ui_process():
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)
