# RoachFlix

Family movie and TV show tracker. Dark, poster-first UI inspired by Apple TV and Letterboxd. Runs on a Raspberry Pi 5 (PinkiPi) behind a Cloudflare Tunnel.

---

## Features

- **Search & Add** — TMDB-powered search with large poster art; one-tap add with Want / Watching / Watched status
- **Auto-categorize** — Movies, TV Shows, and Anime (JP animation auto-detected); manually overrideable per user
- **Streaming Availability** — per-title page shows where to stream it today (US, via TMDB Watch Providers)
- **Daily Notifications** — Telegram alerts when a show you're Watching gets a new episode, or a Want movie lands on streaming
- **Google Calendar** — one-tap to add premiere or next-episode dates to Google Calendar
- **Family accounts** — four users (Homie, Gillian, Loren, Blythe) each with their own list; family view shows everyone's status
- **TV-first UI** — dark background, full-bleed posters, Tailwind CSS, mobile and TV-browser friendly

---

## Raspberry Pi Setup

### 1. Clone & install

```bash
git clone https://github.com/roachdaniel/roachflix.git /home/pi/roachflix
cd /home/pi/roachflix
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env        # fill in SECRET_KEY, TMDB_API_KEY, TELEGRAM_BOT_TOKEN
```

The Telegram bot token is read from `/home/pi/.env` (or `TELEGRAM_BOT_TOKEN` env var). Chat ID and topic are set in `telegram_config.py` and match the family Telegram supergroup.

### 3. Initialize the database

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
python seed_users.py   # creates Homie, Gillian, Loren, Blythe
```

Set initial passwords via env before seeding:
```bash
PASSWORD_HOMIE=yourpass PASSWORD_GILLIAN=yourpass ... python seed_users.py
```

### 4. Run as a service

```bash
sudo cp roachflix.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now roachflix
```

### 5. Cloudflare Tunnel

Point your existing Cloudflare tunnel to `http://localhost:5000`.

---

## Google Calendar Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Calendar API
3. Create OAuth2 credentials (Desktop app), download the JSON
4. Run the OAuth flow once locally to generate a token, then set the full JSON as `GOOGLE_CALENDAR_CREDENTIALS_JSON` in `.env`

---

## Telegram Notifications

Alerts go to the **Alerts** topic (thread 10) of the family Telegram supergroup. The bot token is never stored in code — it's read from `/home/pi/.env` at startup.

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session secret — make it long and random |
| `TMDB_API_KEY` | Free API key from themoviedb.org |
| `TELEGRAM_BOT_TOKEN` | Bot token (never hardcoded) |
| `GOOGLE_CALENDAR_CREDENTIALS_JSON` | Full OAuth2 JSON string |

---

## Development

Run locally:
```bash
source venv/bin/activate
flask run --debug
```

All development happens on Vader. Deploy to PinkiPi via git pull + service restart.
