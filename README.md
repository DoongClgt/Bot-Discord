# Discord Bot

A Discord bot for moderation, spam-trap handling, Steam patch/update watching, and a small Flask dashboard.

Vietnamese setup guide: [README_VI.md](README_VI.md)

## Features

- Flask dashboard with Discord-themed sidebar UI (6 pages: Overview with CPU/RAM sparkline + quick actions, Settings, Steam Watcher, Logs, Ban log (history + download), Version). Save Config auto-restarts the bot. UTC+7 timestamps. HTML/CSS/JS split across `templates/index.html`, `static/dashboard.css`, `static/dashboard.js`. Ban events are appended to `data/ban_log.jsonl` and downloadable via `/api/ban_log/download`.
- Discord slash commands and text fallback commands.
- Spam trap flow: assign suspect role, delete trap messages, ban repeat suspects, and a self-updating ban counter in `SUSPECT_CHANNEL_ID`.
- Ban audit log: every ban (including manual admin bans) is logged into `BAN_LOG_THREAD_ID` with audit info.
- Auto-delete embeds by configured target user, keywords, category, and channel filters.
- Steam patch/update watcher using Steam Events with interval or scheduled hours.
- Manage watched Steam games with `/game add`, `/game remove`, `/game list`, and `/game help`.

## Quick Start

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone https://github.com/DoongClgt/Bot-Discord.git
cd Bot-Discord
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Run the bot:

```bash
source .venv/bin/activate
python3 bot.py
```

Run the dashboard:

```bash
source .venv/bin/activate
python3 web.py
```

Or start both on a VPS:

```bash
chmod +x deploy/start_vps.sh
./deploy/start_vps.sh
```

Default dashboard URL:

```text
http://127.0.0.1:5000
```

## Important Environment Keys

```env
DISCORD_TOKEN=''

# Auto-delete embed
TARGET_USER_ID=''
TARGET_KEYWORDS=''
TARGET_CATEGORY_IDS=''
EXCLUDED_CHANNEL_IDS=''

# Spam trap
SUSPECT_CHANNEL_ID=''
SPAM_TRAP_CHANNEL_ID=''
SPAM_TRAP_CHANNEL_ID_2=''
SPAM_TRAP_EXCLUDED_ROLE_IDS=''
SUSPECT_ROLE_ID=''

# Log channels
BAN_LOG_THREAD_ID=''
STARTUP_CHANNEL_ID=''
GENERAL_LOG_CHANNEL_ID=''

# Steam watcher
STEAMDB_PATCH_CHANNEL_ID=''
STEAMDB_PATCH_MENTION_USER_ID=''
STEAMDB_PATCH_MENTION_USER_IDS=''
STEAMDB_APP_IDS=''
STEAMDB_PATCH_INTERVAL_HOURS='1'
STEAMDB_PATCH_SCHEDULE_HOURS='0,6,12,18'
STEAMDB_PATCH_MAJOR_ONLY='false'
STEAMDB_PATCH_LIMIT='25'
STEAM_WATCHER_MAX_AGE_DAYS='7'

# Dashboard
DASHBOARD_HOST='127.0.0.1'
DASHBOARD_PORT='5000'
DASHBOARD_PUBLIC_URL=''
```

Do not commit `.env`; use `.env.example` as the public template.

## Commands

Slash commands:

```text
/ping
/steamdbcheck
/refreshchannels
/check [game]
/dlt [limit]
/game list
/game add <app_id>
/game remove <game>
/game help
```

Text command aliases also available: `/online`, `/status`, `/patchcheck`, `/sdbcheckrecent`, `/patchrecent`, `/rescanchannels`.

Notes:

- Admin commands require `Manage Messages`.
- `/dlt` slash replies ephemerally (visible only to the caller).
- `/check` and `/game remove` slash support autocomplete from the configured game list.
- Steam Watcher uses Steam Partner event type mapping: `event_type=12` is `MAJOR UPDATE`, `event_type=13` is `REGULAR UPDATE`. `STEAMDB_PATCH_MAJOR_ONLY=true` filters to `event_type=12` only.

## Cloudflare Tunnel

Keep the dashboard bound to localhost:

```env
DASHBOARD_HOST='127.0.0.1'
DASHBOARD_PORT='5000'
DASHBOARD_PUBLIC_URL='https://bot.example.com'
```

Point the Cloudflare Tunnel public hostname to:

```text
http://127.0.0.1:5000
```

## Verify

```bash
python3 -m py_compile bot.py web.py
```

```bash
node -e "const fs=require('fs');const s=fs.readFileSync('static/dashboard.js','utf8');new Function(s);console.log('js syntax ok')"
```
