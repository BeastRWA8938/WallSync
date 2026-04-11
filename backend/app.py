import os
import requests
from flask import Flask, render_template, jsonify, request
from icalevents.icalevents import events
from datetime import datetime, timedelta
import msal
from dotenv import load_dotenv

# Load the hidden keys from the .env file
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION (Now securely pulling from .env) ---
GOOGLE_ICS_URL = os.getenv("GOOGLE_ICS_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPES = ["Tasks.ReadWrite"]

cache = msal.SerializableTokenCache()
if os.path.exists("token_cache.bin"): cache.deserialize(open("token_cache.bin", "r").read())
msal_app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)

def get_ms_token():
    accounts = msal_app.get_accounts()
    if accounts:
        result = msal_app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result: return result["access_token"]
    return None

def get_todo_tasks():
    token = get_ms_token()
    if not token: return []
    headers = {'Authorization': 'Bearer ' + token}
    lists_resp = requests.get("https://graph.microsoft.com/v1.0/me/todo/lists", headers=headers).json()
    if 'value' not in lists_resp: return []
        
    all_tasks = []
    for task_list in lists_resp['value']:
        if task_list['displayName'] in ['Tasks', 'Reminders']:
            tasks_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{task_list['id']}/tasks?$filter=status ne 'completed'"
            tasks_resp = requests.get(tasks_url, headers=headers).json()
            if 'value' in tasks_resp:
                for task in tasks_resp['value']:
                    task['list_id'] = task_list['id']
                    all_tasks.append(task)
    return all_tasks

@app.route('/')
def home():
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30) # Pulled 30 days for the calendar view
    try:
        cal_events = events(url=GOOGLE_ICS_URL, start=start_date, end=end_date)
        cal_events.sort(key=lambda x: x.start)
    except:
        cal_events = []
    return render_template('index.html', events=cal_events, tasks=get_todo_tasks())

@app.route('/complete/<list_id>/<task_id>', methods=['POST'])
def complete_task(list_id, task_id):
    token = get_ms_token()
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    requests.patch(f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}", headers=headers, json={"status": "completed"})
    return jsonify({"success": True})

# --- NEW: ADD TASK ROUTE ---
@app.route('/add_task', methods=['POST'])
def add_task():
    token = get_ms_token()
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    
    # 1. Find the default task list ID
    lists = requests.get("https://graph.microsoft.com/v1.0/me/todo/lists", headers=headers).json()
    list_id = next((lst['id'] for lst in lists.get('value', []) if lst['displayName'] in ['Tasks', 'Reminders']), None)
    
    if not list_id: return jsonify({"error": "No list found"}), 400

    data = request.json
    payload = {"title": data.get('title')}
    
    # Handle Optional Date (Locked to IST Timezone)
    if data.get('dueDate'):
        payload["dueDateTime"] = {"dateTime": f"{data.get('dueDate')}T00:00:00", "timeZone": "India Standard Time"}
        
    # Handle Recurrence
    recurrence = data.get('recurrence')
    if recurrence and recurrence != "none":
        payload["recurrence"] = {
            "pattern": {"type": "daily" if recurrence == "daily" else "weekly", "interval": 1},
            "range": {"type": "noEnd"}
        }

    requests.post(f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks", headers=headers, json=payload)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)