# WallSync Frontend

This folder contains the Svelte/Vite SPA for WallSync.

The frontend is intentionally small and static-build friendly. In development it runs through Vite on port `5173`. In wallpaper mode it is compiled to `frontend/dist` and served by Flask from `backend/app.py` on port `5000`.

## Main Files

```text
src/
  App.svelte
  app.css
  components/
    SideBar.svelte
    MainView.svelte
    Header.svelte
    Content.svelte
    TaskView.svelte
    CalendarView.svelte
    HabitsView.svelte
    AIView.svelte
```

## UI Rules

- The app root uses `100vw` and `100vh`.
- Body/page scrolling is disabled with `overflow: hidden`.
- Only specific inner panels should scroll.
- The sidebar is placed on the right side.
- Tab routing is local Svelte state, using `{#if}` blocks instead of a router.

## Commands

Install dependencies:

```powershell
npm install
```

Start Vite dev server:

```powershell
npm.cmd run dev
```

Start Vite with an explicit host:

```powershell
npm.cmd run dev -- --host 127.0.0.1
```

Build static production files:

```powershell
npm.cmd run build
```

Preview the static build with Vite:

```powershell
npm.cmd run preview
```

## Development URL

```text
http://127.0.0.1:5173
```

## Production URL

After running `npm.cmd run build`, start Flask from the project root:

```powershell
.\venv\Scripts\python.exe backend\app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## API Expectations

The frontend should call Flask API routes under `/api`.

Current planned routes:

- `GET /api/tasks`
- `POST /api/tasks`
- `POST /api/tasks/<list_id>/<task_id>/complete`
- `GET /api/calendar/events`
- `GET /api/habits`
- `POST /api/agent/chat`

The AI route is only a placeholder. LangChain/Groq logic can be wired into the Flask backend later.
