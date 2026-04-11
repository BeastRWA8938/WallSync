# WallSync 🔄

A fully interactive, locally hosted "Command Center" dashboard designed specifically for vertical monitors. WallSync acts as a live, interactive wallpaper that syncs directly with Google Calendar and Microsoft To-Do (including Samsung Reminders).

Built for developers who want complete control over their layout without paying for subscription-based dashboard services.

## ✨ Features

* **Two-Way Task Sync:** Pulls active tasks from Microsoft To-Do/Samsung Reminders. You can mark tasks as completed or add new ones directly from your desktop wallpaper.
* **Google Calendar Integration:** Parses private `.ics` feeds to display a daily agenda and a monthly calendar grid.
* **Zero Overhead & 100% Free:** Runs entirely locally using a lightweight Flask backend. No cloud subscriptions, no paywalls.
* **Vertical First UI:** Custom CSS designed specifically for portrait orientation monitors (e.g., 1366x768 rotated).
* **Silent Autostart:** Includes VBScript configurations to boot silently with Windows.
* **Interactive Wallpaper:** Designed to be used seamlessly with [Lively Wallpaper](https://rocksdanister.github.io/lively/).

## 🛠️ Prerequisites

* Python 3.8 or higher
* [Lively Wallpaper](https://rocksdanister.github.io/lively/) (for desktop background integration)
* A Google Calendar Account
* A Microsoft/Outlook Account (for Microsoft To-Do)

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/BeastRWA8938/WallSync.git
cd WallSync
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables

Create a file named `.env` in the root directory. You need to obtain two keys:

1. **Google ICS URL:** Go to Google Calendar -> Settings -> Integrate Calendar -> Copy the "Secret address in iCal format".
2. **Microsoft Client ID:** Go to the [Azure Portal](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade). Create a new App Registration ("Personal accounts only"). Grant it the `Tasks.ReadWrite` Graph API permission. Add `http://localhost:8080` as a "Mobile and desktop applications" Redirect URI.

Add them to your `.env` file like this:

```env
GOOGLE_ICS_URL=https://calendar.google.com/calendar/ical/your_secret_link/basic.ics
CLIENT_ID=your_microsoft_client_id_here
```

### 4. Initial Authentication

Microsoft Graph requires a one-time user login to generate a token cache.

```bash
python auth_setup.py
```

This will open your browser. Log in to your Microsoft account. Once the terminal says "SUCCESS" and generates a `token_cache.bin` file, you never need to run this script again.

### 5. Run the Server

```bash
python app.py
```

Open your browser and navigate to `http://localhost:5000` to preview the dashboard.

## 🖥️ Setting as Wallpaper (Lively)

1. Open Lively Wallpaper.
2. Click **Add Wallpaper**.
3. Enter `http://localhost:5000` as the URL.
4. Assign it to your vertical monitor.
5. *Important:* In Lively settings, go to Wallpaper -> Interaction -> Set Input to "Always" so you can click checkboxes and buttons!

## 👻 Silent Autostart (Windows)

To have WallSync launch invisibly when your PC boots:

1. Edit `start_server.bat` to include your absolute folder path.
2. Create a shortcut of `invisible.vbs`.
3. Press `Win + R`, type `shell:startup`, and press Enter.
4. Drag the shortcut into the Startup folder.

## 🤝 Contributing

Feel free to fork this project and add your own modules (e.g., local weather from an ESP32 sensor, Spotify current playing, etc.). Pull requests are welcome!