# WallSync Docker Deployment & Auto-Start Guide

This guide explains how to build, run, and configure WallSync to automatically start on boot on Windows, macOS, and Linux using Docker.

---

## 🚀 1. Build and Run WallSync

First, ensure you have configured your `.env` file in the root directory:
```env
GOOGLE_ICS_URL=https://calendar.google.com/calendar/ical/.../basic.ics
CLIENT_ID=your_microsoft_client_id_here
DATABASE_URL=postgresql://postgres:[password]@db.[id].supabase.co:5432/postgres
FLASK_ENV=production
```

To build the image and start the container in the background, run:
```bash
docker compose up -d --build
```
This builds the Svelte frontend, compiles it, bundles it inside the Flask backend runtime container, mounts your persistent data directory `./backend/data` (to save your Microsoft login), and serves the app on `http://localhost:5000`.

---

## 🔄 2. Platform-Specific Auto-Start Configuration

Because `docker-compose.yml` has `restart: unless-stopped` set, the container will start automatically whenever the Docker service/daemon starts. We just need to ensure Docker runs on boot on your platform.

### Windows (Docker Desktop)
1. **Enable Docker Desktop on Login:**
   - Open Docker Desktop.
   - Click the gear icon (**Settings**) in the top right.
   - Under **General**, check **"Start Docker Desktop when you log in"**.
   
2. **Alternate: Silent Batch Script (Without opening Docker Desktop window):**
   - Press `Win + R`, type `shell:startup`, and press Enter. This opens your Windows Startup folder.
   - Create a file named `wallsync_start.bat` in that folder with the following contents (replace with the absolute path to your WallSync folder):
     ```cmd
     @echo off
     cd /d "C:\path\to\WallSync - LiveToDoAndCalander"
     docker compose up -d
     ```

---

### macOS (Docker Desktop)
1. **Enable Docker Desktop on Login:**
   - Open Docker Desktop.
   - Click the gear icon (**Settings**).
   - Under **General**, check **"Start Docker Desktop when you log in"**.

2. **Alternate: LaunchAgent Configuration:**
   - Create a LaunchAgent file at `~/Library/LaunchAgents/com.wallsync.startup.plist`:
     ```xml
     <?xml version="1.0" encoding="UTF-8"?>
     <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
     <plist version="1.0">
     <dict>
         <key>Label</key>
         <string>com.wallsync.startup</string>
         <key>ProgramArguments</key>
         <array>
             <string>/usr/local/bin/docker-compose</string>
             <string>-f</string>
             <string>/Users/yourusername/path/to/WallSync - LiveToDoAndCalander/docker-compose.yml</string>
             <string>up</string>
             <string>-d</string>
         </array>
         <key>RunAtLoad</key>
         <true/>
         <key>KeepAlive</key>
         <false/>
     </dict>
     </plist>
     ```
   - Load the agent:
     ```bash
     launchctl load ~/Library/LaunchAgents/com.wallsync.startup.plist
     ```

---

### Linux (Native Docker)
Since Linux runs Docker as a system daemon, it does not require a graphical desktop login to launch.

1. **Enable Docker Daemon on Boot:**
   ```bash
   sudo systemctl enable docker
   sudo systemctl enable containerd
   ```

2. **Confirm Autostart Status:**
   As long as the daemon is active, your container (configured with `restart: unless-stopped` in `docker-compose.yml`) will start up immediately on system boot.
