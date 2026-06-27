import os
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import msal
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from icalevents.icalevents import events

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"
TOKEN_CACHE_PATH = BASE_DIR / "token_cache.bin"
DATABASE_PATH = BASE_DIR / "wallsync.db"

GOOGLE_ICS_URL = os.getenv("GOOGLE_ICS_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPES = ["Tasks.ReadWrite"]

app = Flask(__name__, static_folder=None)

if os.getenv("FLASK_ENV", "development") == "development":
    CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})

cache = msal.SerializableTokenCache()
if TOKEN_CACHE_PATH.exists():
    cache.deserialize(TOKEN_CACHE_PATH.read_text())

msal_app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache) if CLIENT_ID else None


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                ms_task_id TEXT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS completions (
                id INTEGER PRIMARY KEY,
                habit_id INTEGER NOT NULL,
                completed_date TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
                UNIQUE(habit_id, completed_date)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                session_date TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_tasks (
                task_id TEXT PRIMARY KEY,
                completed_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )


init_database()


def persist_token_cache():
    if cache.has_state_changed:
        TOKEN_CACHE_PATH.write_text(cache.serialize())


def get_ms_token():
    if not msal_app:
        return None

    accounts = msal_app.get_accounts()
    if not accounts:
        return None

    result = msal_app.acquire_token_silent(SCOPES, account=accounts[0])
    persist_token_cache()
    return result.get("access_token") if result else None


def graph_headers():
    token = get_ms_token()
    if not token:
        return None
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_default_task_list(headers):
    response = requests.get("https://graph.microsoft.com/v1.0/me/todo/lists", headers=headers, timeout=15)
    response.raise_for_status()
    lists = response.json().get("value", [])
    return next((item for item in lists if item.get("displayName") in ["Tasks", "Reminders"]), None)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "wallsync"})


@app.get("/api/tasks")
def list_tasks():
    headers = graph_headers()
    if not headers:
        return jsonify({"tasks": [], "needsAuth": True})

    task_list = get_default_task_list(headers)
    if not task_list:
        return jsonify({"tasks": []})

    # 1. Fetch active tasks from Microsoft Graph
    url_active = f"https://graph.microsoft.com/v1.0/me/todo/lists/{task_list['id']}/tasks?$filter=status ne 'completed'"
    response = requests.get(url_active, headers=headers, timeout=15)
    response.raise_for_status()
    tasks = response.json().get("value", [])

    # 2. Get the last_sync_time from metadata table
    last_sync_time = None
    with get_db_connection() as connection:
        row = connection.execute("SELECT value FROM sync_metadata WHERE key = 'last_sync_time'").fetchone()
        if row:
            last_sync_time = row["value"]

    if not last_sync_time:
        # Default: 24 hours ago
        last_sync_time = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"

    # Save the current execution time for the next cycle
    current_utc_time = datetime.utcnow().isoformat() + "Z"

    # 3. Fetch recently completed tasks from Microsoft Graph
    completed_tasks = []
    try:
        url_completed = f"https://graph.microsoft.com/v1.0/me/todo/lists/{task_list['id']}/tasks"
        query_params = {
            "$filter": f"status eq 'completed' and lastModifiedDateTime ge {last_sync_time}"
        }
        completed_response = requests.get(url_completed, headers=headers, params=query_params, timeout=15)
        if completed_response.ok:
            completed_tasks = completed_response.json().get("value", [])
    except Exception:
        pass # fallback silently so task loading never breaks if Graph limits filter query format

    # 4. Process completed tasks (deduplication & PC-offline timezone date alignment)
    for c_task in completed_tasks:
        task_id = c_task["id"]
        
        # Check deduplication ledger
        with get_db_connection() as connection:
            row = connection.execute("SELECT 1 FROM processed_tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row:
                continue # Skip already processed task
        
        # Query matching active habits
        title = c_task.get("title", "")
        completed_time_str = c_task.get("completedDateTime", {}).get("dateTime")
        
        # Extract chronological exact date adjusted for system local timezone
        if completed_time_str:
            base_str = completed_time_str.split(".")[0].replace("Z", "")
            try:
                utc_dt = datetime.fromisoformat(base_str).replace(tzinfo=timezone.utc)
                local_dt = utc_dt.astimezone()
                completed_date_str = local_dt.strftime("%Y-%m-%d")
            except ValueError:
                completed_date_str = completed_time_str.split("T")[0]
        else:
            completed_date_str = date.today().isoformat()

        with get_db_connection() as connection:
            habits = connection.execute("SELECT id, name FROM habits").fetchall()

        matched_habit_ids = []
        for habit in habits:
            # Case-insensitive substring match
            if habit["name"].lower() in title.lower():
                matched_habit_ids.append(habit["id"])

        if matched_habit_ids:
            with get_db_connection() as connection:
                for h_id in matched_habit_ids:
                    connection.execute(
                        """
                        INSERT INTO completions (habit_id, completed_date, count)
                        VALUES (?, ?, 1)
                        ON CONFLICT(habit_id, completed_date)
                        DO UPDATE SET count = count + 1
                        """,
                        (h_id, completed_date_str),
                    )

        # Log into processed ledger
        with get_db_connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO processed_tasks (task_id, completed_at) VALUES (?, ?)",
                (task_id, current_utc_time),
            )

    # 5. Save the new last_sync_time into metadata
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO sync_metadata (key, value)
            VALUES ('last_sync_time', ?)
            ON CONFLICT(key)
            DO UPDATE SET value = excluded.value
            """,
            (current_utc_time,),
        )

    # 6. Format and return active tasks
    for task in tasks:
        task["list_id"] = task_list["id"]

    return jsonify({"tasks": tasks})


@app.post("/api/tasks")
def add_task():
    headers = graph_headers()
    if not headers:
        return jsonify({"error": "Microsoft Graph is not authenticated"}), 401

    title = (request.json or {}).get("title", "").strip()
    if not title:
        return jsonify({"error": "Task title is required"}), 400

    task_list = get_default_task_list(headers)
    if not task_list:
        return jsonify({"error": "No default task list found"}), 404

    payload = {"title": title}
    due_date = (request.json or {}).get("dueDate")
    if due_date:
        payload["dueDateTime"] = {"dateTime": f"{due_date}T00:00:00", "timeZone": "India Standard Time"}

    response = requests.post(
        f"https://graph.microsoft.com/v1.0/me/todo/lists/{task_list['id']}/tasks",
        headers=headers,
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return jsonify({"task": response.json()}), 201


@app.post("/api/tasks/<list_id>/<task_id>/complete")
def complete_task(list_id, task_id):
    headers = graph_headers()
    if not headers:
        return jsonify({"error": "Microsoft Graph is not authenticated"}), 401

    title = (request.json or {}).get("title", "").strip()

    # 1. Update status to completed in Microsoft Graph
    response = requests.patch(
        f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}",
        headers=headers,
        json={"status": "completed"},
        timeout=15,
    )
    response.raise_for_status()

    # 2. Process matching habits immediately
    if title:
        with get_db_connection() as connection:
            row = connection.execute("SELECT 1 FROM processed_tasks WHERE task_id = ?", (task_id,)).fetchone()
        
        if not row:
            with get_db_connection() as connection:
                habits = connection.execute("SELECT id, name FROM habits").fetchall()

            matched_habit_ids = []
            for habit in habits:
                if habit["name"].lower() in title.lower():
                    matched_habit_ids.append(habit["id"])

            if matched_habit_ids:
                completed_date_str = date.today().isoformat()
                
                with get_db_connection() as connection:
                    for h_id in matched_habit_ids:
                        connection.execute(
                            """
                            INSERT INTO completions (habit_id, completed_date, count)
                            VALUES (?, ?, 1)
                            ON CONFLICT(habit_id, completed_date)
                            DO UPDATE SET count = count + 1
                            """,
                            (h_id, completed_date_str),
                        )

            # Log to deduplication processed ledger
            current_utc_time = datetime.utcnow().isoformat() + "Z"
            with get_db_connection() as connection:
                connection.execute(
                    "INSERT OR IGNORE INTO processed_tasks (task_id, completed_at) VALUES (?, ?)",
                    (task_id, current_utc_time),
                )

    return jsonify({"success": True})


@app.get("/api/calendar/events")
def calendar_events():
    if not GOOGLE_ICS_URL:
        return jsonify({"events": []})

    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        return jsonify({"error": "days must be an integer"}), 400

    start = datetime.now()
    end = start + timedelta(days=days)
    try:
        cal_events = events(url=GOOGLE_ICS_URL, start=start, end=end)
    except Exception as exc:
        return jsonify({"error": str(exc), "events": []}), 502

    parsed_events = [
        {
            "summary": event.summary,
            "start": event.start.isoformat(),
            "end": event.end.isoformat(),
            "location": event.location,
        }
        for event in sorted(cal_events, key=lambda item: item.start)
    ]
    return jsonify({"events": parsed_events})


@app.get("/api/habits")
def list_habits():
    end_date = date.today()
    start_date = end_date - timedelta(days=220)

    with get_db_connection() as connection:
        habits = connection.execute(
            """
            SELECT id, name, ms_task_id
            FROM habits
            ORDER BY id DESC
            """
        ).fetchall()
        completions = connection.execute(
            """
            SELECT habit_id, completed_date, count
            FROM completions
            WHERE completed_date BETWEEN ? AND ?
            ORDER BY completed_date ASC
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

    completions_by_habit = {}
    for completion in completions:
        completions_by_habit.setdefault(completion["habit_id"], []).append(
            {
                "date": completion["completed_date"],
                "count": completion["count"],
            }
        )

    return jsonify(
        {
            "habits": [
                {
                    "id": habit["id"],
                    "name": habit["name"],
                    "ms_task_id": habit["ms_task_id"],
                    "completions": completions_by_habit.get(habit["id"], []),
                }
                for habit in habits
            ]
        }
    )


@app.post("/api/habits")
def create_habit():
    payload = request.json or {}
    name = payload.get("name", "").strip()
    ms_task_id = payload.get("ms_task_id")

    if not name:
        return jsonify({"error": "Habit name is required"}), 400

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO habits (name, ms_task_id)
            VALUES (?, ?)
            """,
            (name, ms_task_id),
        )
        habit_id = cursor.lastrowid

    return jsonify({"habit": {"id": habit_id, "name": name, "ms_task_id": ms_task_id, "completions": []}}), 201


@app.post("/api/habits/<int:habit_id>/increment")
def increment_habit(habit_id):
    today = date.today().isoformat()

    with get_db_connection() as connection:
        habit = connection.execute("SELECT id FROM habits WHERE id = ?", (habit_id,)).fetchone()
        if not habit:
            return jsonify({"error": "Habit not found"}), 404

        connection.execute(
            """
            INSERT INTO completions (habit_id, completed_date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(habit_id, completed_date)
            DO UPDATE SET count = count + 1
            """,
            (habit_id, today),
        )
        completion = connection.execute(
            """
            SELECT completed_date, count
            FROM completions
            WHERE habit_id = ? AND completed_date = ?
            """,
            (habit_id, today),
        ).fetchone()

    return jsonify({"date": completion["completed_date"], "count": completion["count"]})


@app.post("/api/habits/<int:habit_id>/decrement")
def decrement_habit(habit_id):
    today = date.today().isoformat()

    with get_db_connection() as connection:
        habit = connection.execute("SELECT id FROM habits WHERE id = ?", (habit_id,)).fetchone()
        if not habit:
            return jsonify({"error": "Habit not found"}), 404

        completion = connection.execute(
            """
            SELECT count
            FROM completions
            WHERE habit_id = ? AND completed_date = ?
            """,
            (habit_id, today),
        ).fetchone()

        if not completion:
            return jsonify({"date": today, "count": 0})

        if completion["count"] <= 1:
            connection.execute(
                """
                DELETE FROM completions
                WHERE habit_id = ? AND completed_date = ?
                """,
                (habit_id, today),
            )
            count = 0
        else:
            connection.execute(
                """
                UPDATE completions
                SET count = count - 1
                WHERE habit_id = ? AND completed_date = ?
                """,
                (habit_id, today),
            )
            count = completion["count"] - 1

    return jsonify({"date": today, "count": count})


@app.post("/api/agent/chat")
def agent_chat():
    return jsonify({"reply": "Agent hook is ready. LangChain logic can be wired here later."})


@app.get("/api/focus/sessions")
def list_focus_sessions():
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, topic, start_time, end_time, duration_seconds, session_date
            FROM focus_sessions
            ORDER BY id DESC
            """
        ).fetchall()
    
    sessions = [
        {
            "id": row["id"],
            "topic": row["topic"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "duration_seconds": row["duration_seconds"],
            "session_date": row["session_date"]
        }
        for row in rows
    ]
    return jsonify({"sessions": sessions})


@app.post("/api/focus/sessions")
def create_focus_session():
    payload = request.json or {}
    topic = payload.get("topic", "").strip()
    start_time = payload.get("start_time", "").strip()
    end_time = payload.get("end_time", "").strip()
    duration_seconds = payload.get("duration_seconds")

    if not topic or not start_time or not end_time or duration_seconds is None:
        return jsonify({"error": "Missing required focus session details"}), 400

    if topic not in ["Study", "Gaming", "Timepass", "Productive"]:
        return jsonify({"error": "Invalid focus session topic"}), 400

    inserted_sessions = []
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    current_start = start_dt
    with get_db_connection() as connection:
        while current_start.date() < end_dt.date():
            next_midnight = datetime(current_start.year, current_start.month, current_start.day) + timedelta(days=1)
            duration = int((next_midnight - current_start).total_seconds())
            
            s_date = current_start.date().isoformat()
            cursor = connection.execute(
                """
                INSERT INTO focus_sessions (topic, start_time, end_time, duration_seconds, session_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (topic, current_start.isoformat(), next_midnight.isoformat(), duration, s_date),
            )
            inserted_sessions.append({
                "id": cursor.lastrowid,
                "topic": topic,
                "start_time": current_start.isoformat(),
                "end_time": next_midnight.isoformat(),
                "duration_seconds": duration,
                "session_date": s_date
            })
            current_start = next_midnight

        # final remainder segment
        duration = int((end_dt - current_start).total_seconds())
        if duration > 0:
            s_date = current_start.date().isoformat()
            cursor = connection.execute(
                """
                INSERT INTO focus_sessions (topic, start_time, end_time, duration_seconds, session_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (topic, current_start.isoformat(), end_dt.isoformat(), duration, s_date),
            )
            inserted_sessions.append({
                "id": cursor.lastrowid,
                "topic": topic,
                "start_time": current_start.isoformat(),
                "end_time": end_dt.isoformat(),
                "duration_seconds": duration,
                "session_date": s_date
            })

    return jsonify({"sessions": inserted_sessions}), 201


@app.delete("/api/focus/sessions/<int:session_id>")
def delete_focus_session(session_id):
    with get_db_connection() as connection:
        session = connection.execute("SELECT id FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            return jsonify({"error": "Focus session not found"}), 404
        
        connection.execute("DELETE FROM focus_sessions WHERE id = ?", (session_id,))
    
    return jsonify({"success": True})


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    requested = FRONTEND_DIST / path
    if path and requested.exists():
        return send_from_directory(FRONTEND_DIST, path)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return send_from_directory(FRONTEND_DIST, "index.html")

    return jsonify(
        {
            "error": "Frontend build not found",
            "hint": "Run `npm run build` inside the frontend folder before production wallpaper mode.",
        }
    ), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_ENV", "development") == "development")
