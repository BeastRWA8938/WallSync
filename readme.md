# WallSync

WallSync is a locally hosted command-center dashboard designed to run as an interactive desktop wallpaper through Lively Wallpaper on a vertical monitor.

The app uses a lightweight Svelte/Vite frontend and a Flask backend. During development, Vite and Flask can run on separate ports. For production and wallpaper mode, the Svelte app is built into static files and served directly by Flask on a single port: `http://127.0.0.1:5000`.

## Current Stack

- Frontend: Svelte + Vite
- Backend: Python + Flask
- Dev CORS: Flask-Cors for `/api/*`
- Tasks: Microsoft Graph API through MSAL
- Calendar: Google Calendar private `.ics` feed through `icalevents`
- Habits: local Flask endpoint placeholder, ready for SQLite or JSON storage
- AI Agent: Flask endpoint placeholder, ready for LangChain/Groq integration later

## Project Structure

```text
WallSync - LiveToDoAndCalander/
  backend/
    app.py
    auth_setup.py
    token_cache.bin
  frontend/
    src/
      App.svelte
      app.css
      components/
    dist/
  requirements.txt
  start_server.bat
  invisible.vbs
```

## Requirements

- Node.js and npm
- Python 3.10 or newer
- Lively Wallpaper, for wallpaper mode
- Microsoft account, for Microsoft To Do
- Google Calendar private ICS URL, for calendar events

## First-Time Setup

Install frontend dependencies:

```powershell
cd frontend
npm install
```

Create and install backend dependencies:

```powershell
cd ..
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GOOGLE_ICS_URL=https://calendar.google.com/calendar/ical/your_secret_link/basic.ics
CLIENT_ID=your_microsoft_client_id_here
FLASK_ENV=development
```

Run one-time Microsoft authentication:

```powershell
cd backend
..\venv\Scripts\python.exe auth_setup.py
```

## Development Mode

Run Flask API on port `5000`:

```powershell
.\venv\Scripts\python.exe backend\app.py
```

Run Svelte/Vite on port `5173`:

```powershell
cd frontend
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:5173
```

In development, the frontend can call Flask API routes at:

```text
http://127.0.0.1:5000/api/...
```

## Production / Wallpaper Mode

Build the frontend:

```powershell
cd frontend
npm.cmd run build
```

Start Flask from the project root:

```powershell
cd ..
.\venv\Scripts\python.exe backend\app.py
```

Open:

```text
http://127.0.0.1:5000
```

Flask serves `frontend/dist/index.html` and the compiled static assets. No Node.js server is needed in production.

## API Routes

- `GET /api/health`
- `GET /api/tasks`
- `POST /api/tasks`
- `POST /api/tasks/<list_id>/<task_id>/complete`
- `GET /api/calendar/events`
- `GET /api/habits`
- `POST /api/agent/chat`

## Lively Wallpaper Setup

1. Build the frontend with `npm.cmd run build`.
2. Start Flask on `http://127.0.0.1:5000`.
3. Open Lively Wallpaper.
4. Add a URL wallpaper using `http://127.0.0.1:5000`.
5. Assign it to the vertical monitor.
6. Enable wallpaper interaction in Lively settings so buttons and inputs can receive clicks.

## Windows Autostart

`start_server.bat` is intended to launch Flask. If your folder location changes, update the `cd` path inside that file.

To run silently on startup:

```powershell
Win + R
shell:startup
```

Place a shortcut to `invisible.vbs` in that startup folder.

## Troubleshooting

If PowerShell blocks `npm` scripts, use:

```powershell
npm.cmd run dev
npm.cmd run build
```

If Python opens the Microsoft Store or reports a WindowsApps path, install Python normally from python.org and recreate the virtual environment:

```powershell
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

If Flask says the frontend build is missing, run:

```powershell
cd frontend
npm.cmd run build
```
