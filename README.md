# 🌸 Ayushi Life OS — Backend Setup

## What's included
- **server.py** — Python/Flask backend with SQLite database
- **static/** — Your beautiful iOS-ready app
- **ayushi.db** — Created automatically when you first run the server (all your data lives here)
- **START.bat** — Double-click to launch on Windows

---

## Quick Start (Windows)

### Step 1 — Install Python
If you don't have Python:
1. Go to https://python.org/downloads
2. Download the latest Python 3.x
3. During install, **check "Add Python to PATH"** ✅

### Step 2 — Start the server
Double-click **START.bat** — it will:
- Install Flask automatically
- Start the server at http://localhost:5000
- Keep your data in `ayushi.db`

### Step 3 — Use on your iPhone
1. Make sure your iPhone and PC are on the **same WiFi**
2. Open a new terminal and run: `ipconfig`
3. Find your **IPv4 Address** (looks like 192.168.x.x)
4. Open **Safari** on iPhone → go to `http://192.168.x.x:5000`
5. Tap the **Share button** → **"Add to Home Screen"**
6. Name it "Ayushi OS" → **Add**
7. It's now on your home screen like a real app! 🌸

---

## API Endpoints (for your reference)

| Method | Endpoint | What it does |
|--------|----------|-------------|
| GET | `/api/day/YYYY-MM-DD` | Load a day's data |
| POST | `/api/day/YYYY-MM-DD` | Save day + get scores + analysis |
| GET | `/api/analysis/YYYY-MM-DD` | Get detailed analysis for any day |
| GET | `/api/stats` | Streaks, XP, averages, gym count |
| GET | `/api/history?days=28` | Heatmap data |
| GET | `/api/history/all` | Every day ever logged |
| POST | `/api/gym` | Save workout |
| GET | `/api/gym/YYYY-MM-DD` | Load a day's gym log |
| GET | `/api/goals` | All goals |
| POST | `/api/goals` | Add a goal |
| PATCH | `/api/goals/:id` | Update goal progress |
| GET | `/api/journal/YYYY-MM-DD` | Load journal |
| POST | `/api/journal/YYYY-MM-DD` | Save journal |

---

## Backup your data
Your database is `ayushi.db` in this folder.
Copy it to Google Drive / OneDrive regularly to back it up.

To restore: just replace the file.

---

## Run from anywhere (optional - make it always available)

### Option A: Keep PC on + always run START.bat
Simple. Works on your home network.

### Option B: Deploy to Railway (free cloud hosting)
1. Go to https://railway.app and sign up
2. Create new project → Deploy from GitHub
3. Push this folder to a GitHub repo
4. Railway auto-detects Python + runs it
5. You get a permanent URL like `ayushi-os.railway.app`
6. Add to iPhone home screen with that URL — works anywhere!

### Option C: Render.com (also free)
Same as above but at https://render.com

---

## Keeping data safe on cloud deployment
Set environment variable: `SECRET_KEY=your-secret-string-here`

---

Made with 💖 for Ayushi
