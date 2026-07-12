# Discord Bot

A Discord bot for moderation, spam-trap handling, Steam patch/update watching, and a small Flask dashboard.

Vietnamese setup guide: [README_VI.md](README_VI.md)

## Features

- Flask dashboard with Discord-themed sidebar UI (Overview with CPU/RAM sparkline + quick actions, Settings, Steam Watcher, TikTok downloader, Logs, Ban log (history + download), Tickets, Version). Save Config auto-restarts the bot. UTC+7 timestamps. HTML/CSS/JS split across `templates/index.html`, `static/dashboard.css`, `static/dashboard.js`. Ban events are appended to `data/ban_log.jsonl` and downloadable via `/api/ban_log/download`.
- Discord slash commands and text fallback commands.
- Spam trap flow: anyone who chats in a configured trap channel is banned immediately (excluded roles only get their message deleted), with a self-updating ban counter in both trap channels.
- Ban audit log: every ban (including manual admin bans) is logged into `BAN_LOG_THREAD_ID` with audit info, and appended to `data/ban_log.jsonl` with a `source` field (`spam_trap` or `admin`) plus `banned_by_id` / `banned_by_name` / `banned_by_display_name`. The spam-trap counter ignores `admin` rows.
- Auto-delete embeds by configured target user, keywords, category, and channel filters.
- Auto-assign a default role to new members joining the server (skipped if they already have it).
- Steam patch/update watcher using Steam Events with interval (minutes or hours) or scheduled hours.
- Manage watched Steam games with `/game add`, `/game remove`, `/game list`, and `/game help`.
- Download watermark-free TikTok & Douyin videos/photos from the **dashboard** ("Tải TikTok" page). *(The in-Discord `/tiktok` command is currently disabled.)*

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

For production, prefer systemd (ensures a single bot instance — two concurrent bot
processes would produce duplicate bans/log entries, since the idempotency guard is
per-process):

```bash
sudo bash deploy/install_systemd.sh          # or: sudo RUN_USER=youruser bash deploy/install_systemd.sh
```

This installs `bot-discord-bot.service` + `bot-discord-dashboard.service` and a polkit
rule so the dashboard/deploy can control them without sudo. Once on systemd, don't run
`start_vps.sh` (it would spawn duplicates); `deploy_from_webhook.sh` auto-detects the
services and restarts via systemd.

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
# Trap channels: comma-separated IDs, as many as you want. Editable from the dashboard.
SPAM_TRAP_CHANNEL_IDS=''
SPAM_TRAP_EXCLUDED_ROLE_IDS=''
# Seconds of the banned user's messages Discord deletes across all channels (default 3600 = 1 hour, max 604800).
SPAM_TRAP_BAN_DELETE_SECONDS='3600'

# Log channels
BAN_LOG_THREAD_ID=''
STARTUP_CHANNEL_ID=''
GENERAL_LOG_CHANNEL_ID=''

# Auto role for new members (leave empty to disable)
NEW_MEMBER_ROLE_ID=''
# Toggle the on-join handler without clearing the role ID above
AUTO_ROLE_ON_JOIN_ENABLED='true'

# Ticket system
TICKET_CATEGORY_ID=''
TICKET_CONFIRMED_CATEGORY_ID=''
TICKET_CLOSED_CATEGORY_ID=''
TICKET_SUPPORT_ROLE_IDS=''
TICKET_LOG_CHANNEL_ID=''
TICKET_PANEL_TITLE=''
TICKET_PANEL_DESCRIPTION=''

# Steam watcher
STEAMDB_PATCH_CHANNEL_ID=''
STEAMDB_PATCH_MENTION_USER_ID=''
STEAMDB_PATCH_MENTION_USER_IDS=''
STEAMDB_APP_IDS=''
STEAMDB_PATCH_INTERVAL_HOURS='1'
STEAMDB_PATCH_INTERVAL_MINUTES=''
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
/synccounter
/game list
/game add <app_id>
/game remove <game>
/game help
/ticket_panel
```

`/synccounter` recomputes the spam-trap ban counter from `data/ban_log.jsonl` (admin bans excluded) and updates the counter message (also available as the "Cập nhật số đếm ban" dashboard button / IPC `recount_ban_counter`).

Text command aliases also available: `/online`, `/status`, `/patchcheck`, `/sdbcheckrecent`, `/patchrecent`, `/rescanchannels`, `/recount`, `/recountban`.

## TikTok / Douyin Downloader (dashboard)

- Open the **Tải TikTok** page in the sidebar, paste a TikTok or Douyin link, click **Lấy video** — it shows a preview (cover, title, author) and download buttons that save the **watermark-free** video/images straight to your computer via the browser. Endpoints: `POST /api/tiktok/resolve`, `GET /api/tiktok/download`; tikwm API core in `tiktok_api.py`.
- Backed by the `tikwm.com` API — no extra dependency (no yt-dlp/ffmpeg).
- Saved files are named after the clip title + video id (e.g. `Clip title_7660736561704717620.mp4`) to avoid collisions.
- Douyin links: tikwm doesn't support them, so it parses the Douyin share page directly and picks the watermark-free source.
- **The in-Discord `/tiktok` command is disabled** (`downloader.py` is not imported in `bot.py`). To re-enable: uncomment the `import downloader` line and restart the bot.

## Auto Role For New Members

Set `NEW_MEMBER_ROLE_ID` so the bot assigns that role to every member who joins.

- Bots and members who already have the role are skipped (idempotent).
- The bot needs `Manage Roles` and its highest role must sit **above** the target role.
- Leave the variable empty to disable. Requires the `Server Members` privileged intent to be enabled in the Discord Developer Portal.
- `AUTO_ROLE_ON_JOIN_ENABLED` toggles the on-join handler on/off without clearing the role ID. Defaults to `true`; set to `false`/`0`/`off`/`no` (or empty) to disable.
- Logged to `bot_events.log` under event `auto_role` (success, missing role, Forbidden, HTTP error).
- Dashboard: pick **Bật/Tắt** in "Tự cấp role khi member join" and enter the Role ID under "Role tự cấp cho thành viên mới", then click Save — the bot restarts automatically. The resolved role name is shown right under the input.

## Ticket System

Inspired by Ticket Tool / Tickety. Users open a private channel via a panel button; staff respond inside; on close the bot saves a text transcript and deletes the channel.

- `/ticket_panel` (slash, requires `Manage Server`): posts an embed with a "🎫 Tạo ticket" button in the current channel. Re-runnable; old panels still work after restart thanks to persistent views.
- Panel embed title + description are customizable via `TICKET_PANEL_TITLE` and `TICKET_PANEL_DESCRIPTION` (markdown + newlines supported). Empty falls back to defaults. Edit on dashboard → Cấu hình → Ticket; bot restart applies it, but existing posted panels keep their old text — re-run `/ticket_panel` to refresh.
- Click the panel button → bot creates a private text channel `NNNN-<username>` under `TICKET_CATEGORY_ID` (the **pending** category). Only the requester, the bot, and every role in `TICKET_SUPPORT_ROLE_IDS` (comma-separated) can see it (`@everyone` view denied). One open ticket per user — clicking again returns the existing channel.
- Inside the ticket: bot pings **only the requester** (support roles never get pinged — they see the channel via the pending category) and shows three persistent buttons (support-only): **✅ Xác nhận**, **🔒 Close**, **🗑️ Delete**.
- **Xác nhận** → records `confirmed_by`/`confirmed_at`, renames the channel to `NNNN-<staff>-<user>` (lowercased, sanitized to `[a-z0-9-]`, capped at 100 chars), and if `TICKET_CONFIRMED_CATEGORY_ID` is set moves the channel there via `channel.edit(name=..., category=...)`. Per-channel overwrites are preserved (no `sync_permissions`), so privacy stays intact. Can only be confirmed once. Note Discord's rate limit: 2 renames per 10 minutes per channel.
- **Close** → records `closed_by`/`closed_at` and, if `TICKET_CLOSED_CATEGORY_ID` is set, moves the channel there (archived). Channel is NOT deleted; no transcript created. State stays in `data/tickets.json` until Delete.
- **Delete** → confirm ephemeral → records `deleted_by`/`deleted_at`, generates transcript, posts to log channel, deletes the channel. This is the only action that creates a transcript file.
- Transcript creation (only on **Delete**):
  - Bot dumps full message history into a `.txt` transcript (timestamp, author, content, embeds, attachment URLs).
  - Saves to `data/transcripts/ticket-NNNN-<channelId>.txt` and appends a record to `data/transcripts_index.jsonl`.
  - If `TICKET_LOG_CHANNEL_ID` is set, posts an embed summary + transcript file there.
  - Sleeps 3s, then deletes the channel.
- Manual channel delete (no Close button) → `on_guild_channel_delete` cleans the entry from `data/tickets.json` and logs `ticket_orphan`.
- Counter persists in `data/tickets_counter.txt` (monotonically increasing across restarts).
- Required bot permissions: `Manage Channels`, `Manage Messages`, `View Channel`, `Send Messages`, `Read Message History`, `Embed Links`, `Attach Files`.
- Dashboard: **Tickets** page lists all closed transcripts with a per-row "Tải .txt" button and a header "Tải tất cả (.zip)" button. Endpoints: `GET /api/tickets/transcripts`, `GET /api/tickets/transcripts/<filename>`, `GET /api/tickets/transcripts/download_all` (zips `data/transcripts/*.txt` + `transcripts_index.jsonl` in-memory, no temp files). The 3 IDs show up as read-only chips in the **Cấu hình** page under "Ticket system".
- Events logged: `ticket_open`, `ticket_confirm`, `ticket_close`, `ticket_delete`, `ticket_orphan`.

Notes:

- Admin commands require `Manage Messages`.
- `/dlt` slash replies ephemerally (visible only to the caller).
- `/check` and `/game remove` slash support autocomplete from the configured game list.
- Steam Watcher uses Steam Partner event type mapping: `event_type=12` is `SMALL UPDATE / PATCH NOTES`, `event_type=13` is `REGULAR UPDATE`, `event_type=14` is `MAJOR UPDATE`. It also reads `event_type=28` news items when the title looks like patch/update notes.

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
python3 -m py_compile bot.py core.py moderation.py steam.py tickets.py web.py
```

```bash
node -e "const fs=require('fs');const s=fs.readFileSync('static/dashboard.js','utf8');new Function(s);console.log('js syntax ok')"
```
