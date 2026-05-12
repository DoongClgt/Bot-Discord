# Discord Bot

A Discord bot for moderation, spam-trap handling, Steam patch/update watching, and a small Flask dashboard.

Vietnamese setup guide: [README_VI.md](README_VI.md)

## Features

- Flask dashboard with Discord-themed sidebar UI (6 pages: Overview with CPU/RAM sparkline + quick actions, Settings, Steam Watcher, Logs, Ban log (history + download), Version). Save Config auto-restarts the bot. UTC+7 timestamps. HTML/CSS/JS split across `templates/index.html`, `static/dashboard.css`, `static/dashboard.js`. Ban events are appended to `data/ban_log.jsonl` and downloadable via `/api/ban_log/download`.
- Discord slash commands and text fallback commands.
- Spam trap flow: anyone who chats in a configured trap channel is banned immediately (excluded roles only get their message deleted), with a self-updating ban counter in both trap channels.
- Ban audit log: every ban (including manual admin bans) is logged into `BAN_LOG_THREAD_ID` with audit info.
- Auto-delete embeds by configured target user, keywords, category, and channel filters.
- Auto-assign a default role to new members joining the server (skipped if they already have it).
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
SPAM_TRAP_CHANNEL_ID=''
SPAM_TRAP_CHANNEL_ID_2=''
SPAM_TRAP_EXCLUDED_ROLE_IDS=''

# Log channels
BAN_LOG_THREAD_ID=''
STARTUP_CHANNEL_ID=''
GENERAL_LOG_CHANNEL_ID=''

# Auto role for new members (leave empty to disable)
NEW_MEMBER_ROLE_ID=''
# Toggle the on-join handler without clearing the role ID above
AUTO_ROLE_ON_JOIN_ENABLED='true'

# Steam watcher
STEAMDB_PATCH_CHANNEL_ID=''
STEAMDB_PATCH_MENTION_USER_ID=''
STEAMDB_PATCH_MENTION_USER_IDS=''
STEAMDB_APP_IDS=''
STEAMDB_PATCH_INTERVAL_HOURS='1'
STEAMDB_PATCH_SCHEDULE_HOURS='0,6,12,18'
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
/syncrole
```

Text command aliases also available: `/online`, `/status`, `/patchcheck`, `/sdbcheckrecent`, `/patchrecent`, `/rescanchannels`.

## Auto Role For New Members

Set `NEW_MEMBER_ROLE_ID` so the bot assigns that role to every member who joins.

- Bots and members who already have the role are skipped (idempotent).
- The bot needs `Manage Roles` and its highest role must sit **above** the target role.
- Leave the variable empty to disable. Requires the `Server Members` privileged intent to be enabled in the Discord Developer Portal.
- `AUTO_ROLE_ON_JOIN_ENABLED` toggles the on-join handler on/off without clearing the role ID. Defaults to `true`; set to `false`/`0`/`off`/`no` (or empty) to disable. `/syncrole` ignores this flag.
- Logged to `bot_events.log` under event `auto_role` (success, missing role, Forbidden, HTTP error).
- Dashboard: pick **Bật/Tắt** in "Tự cấp role khi member join" and enter the Role ID under "Role tự cấp cho thành viên mới", then click Save — the bot restarts automatically. The resolved role name is shown right under the input.
- `/syncrole` (slash + text alias `/syncroles`): scans all current members and grants the role to anyone missing it. Requires `Manage Roles`. Replies ephemerally. Sleeps 0.5s between grants to avoid rate limits. Logs to event `auto_role_sync`.
- Dashboard shows a **"Tiến độ /syncrole"** card on the Overview tab: progress bar + Granted/Skipped/Failed chips + start/finish timestamps. The bot writes `data/syncrole_progress.json` every ~1s, the dashboard polls every 2s, and the card stays hidden until `/syncrole` has been run at least once. A toast fires when the run finishes.

Notes:

- Admin commands require `Manage Messages`.
- `/dlt` slash replies ephemerally (visible only to the caller).
- `/check` and `/game remove` slash support autocomplete from the configured game list.
- Steam Watcher uses Steam Partner event type mapping: `event_type=12` is `SMALL UPDATE / PATCH NOTES`, `event_type=13` is `REGULAR UPDATE`, `event_type=14` is `MAJOR UPDATE`. All three are fetched.

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
