# Bot Overview For Agents

Compact handoff for this Discord bot. Keep secrets out of responses.

## Files

```text
bot.py                 Discord bot: events, tasks, commands, IPC consumer
web.py                 Flask dashboard/API, edits .env, writes IPC files
templates/index.html   Dashboard UI; no sidebar, full-width layout
.env                   Runtime config; contains real token/IDs
data/channels.json     Cached ID -> display name for channels/roles/users/threads
data/bot_events.log    JSONL event log shown on dashboard
data/steamdb_patches.json  Seen SteamDB/Steam patch/news IDs
data/spam_trap_state.json  Spam trap ban counter + counter message ID
data/ipc_cmd.txt       Dashboard -> bot command queue
data/ipc_response.txt  Bot -> dashboard command result
```

Dashboard: `http://127.0.0.1:5000`.

## VPS Dashboard With Cloudflare Tunnel

Recommended `.env` values on the VPS:

```env
DASHBOARD_HOST='127.0.0.1'
DASHBOARD_PORT='5000'
DASHBOARD_PUBLIC_URL='https://bot.example.com'
```

Keep `DASHBOARD_HOST` as `127.0.0.1` when using Cloudflare Tunnel. The Flask dashboard stays private on the VPS, and `cloudflared` exposes it through your Cloudflare hostname.

Example tunnel target:

```text
http://127.0.0.1:5000
```

Run the dashboard:

```bash
python3 web.py
```

Then configure Cloudflare Tunnel public hostname to route your domain, for example `bot.example.com`, to `http://127.0.0.1:5000`.

## Current Shape

- Dashboard is full-width with no left sidebar.
- Dashboard tabs: `Dieu khien` for status/actions/config and `Log gan day` for the event log table.
- Config save/reload buttons are at the top of the config form.
- `Log gan day` reads `/api/logs`, backed by `data/bot_events.log`.
- Bot-generated timestamps use `dd-mm-yyyy`.
- Channel/category/role/thread IDs are edited only in `.env`; dashboard shows them as read-only chips from `data/channels.json`.
- Removed features: OTA zip upload and giveaway.
- IPC commands from dashboard: `steamdb_check`, `refresh_channels`.
- Slash commands sync as guild-only in `on_ready()`, then global commands are cleared.

## Commands

Text fallback commands:

```text
/ping / /online / /status
/steamdbcheck / /patchcheck
/check [index|SteamAppID|game name]
/dlt [limit]
/game list
/game add <SteamAppID>
/game remove <index|SteamAppID|game name>
/refreshchannels / /rescanchannels
```

Native slash commands:

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

Admin-like commands require `Manage Messages`. `/check` and `/game remove` autocomplete from configured `STEAMDB_APP_IDS`.

## Core Behavior

Spam trap env keys:

```env
SPAM_TRAP_CHANNEL_ID=''
SPAM_TRAP_CHANNEL_ID_2=''
SUSPECT_CHANNEL_ID=''
SUSPECT_ROLE_NAME='Nghi Pham'
BAN_LOG_THREAD_ID=''
```

- Spam trap uses `SPAM_TRAP_CHANNEL_ID` and optional `SPAM_TRAP_CHANNEL_ID_2`: any member who chats in either trap channel gets `SUSPECT_ROLE_NAME` and their trap message is deleted.
- `SUSPECT_CHANNEL_ID` also marks members as suspects: any member who chats there gets `SUSPECT_ROLE_NAME` and their message is deleted.
- If a member who already has `SUSPECT_ROLE_NAME` chats in either trap channel, the bot deletes the message, bans the member, asks Discord to delete that user's last 60 seconds of messages, writes ban log, and updates the counter.
- On startup the bot ensures `SUSPECT_CHANNEL_ID` has `Số mít tơ bít đã ban: <count>`.
- Spam trap ban counter state is stored in `data/spam_trap_state.json`.
- Auto-delete removes embeds from `TARGET_USER_ID` when embed text contains `TARGET_KEYWORDS`.
- Auto-delete scope: `TARGET_CATEGORY_IDS`, excluding `EXCLUDED_CHANNEL_IDS`.
- Auto-delete writes only to the dashboard event log; it no longer sends Discord delete-log messages.
- `/dlt [limit]` scans channels and active threads under `TARGET_CATEGORY_IDS`, skips `EXCLUDED_CHANNEL_IDS`, checks up to 500 recent messages per channel/thread, and deletes matching messages from `TARGET_USER_ID`.

## Steam Watcher

Important env keys:

```env
STEAMDB_PATCH_CHANNEL_ID=''
STEAMDB_APP_IDS=''
STEAMDB_PATCH_SCHEDULE_HOURS='0,6,12,18'
STEAMDB_PATCH_MAJOR_ONLY='false'
STEAMDB_PATCH_LIMIT='25'
STEAM_WATCHER_MAX_AGE_DAYS='7'
```

- Watcher starts only if `STEAMDB_PATCH_CHANNEL_ID` is set.
- Schedule uses fixed local clock hours; restart does not shift the schedule.
- `STEAMDB_APP_IDS` supports `730,570` and `730_Counter-Strike 2, 570_Dota 2`.
- `/game add` fetches the Steam Store name, writes `.env`, and reloads runtime config.
- Watcher merges SteamDB patchnotes with Steam Web API items whose title looks like patch/update/hotfix/version notes; it filters general announcements/media/news, ignores Steam Web API items older than `STEAM_WATCHER_MAX_AGE_DAYS`, and sends only the newest unseen item per scheduled check.
- Manual `/steamdbcheck` sends the newest unseen item; if everything is already seen, it sends the newest matching patch/news again for testing.
- Seen IDs are stored in `data/steamdb_patches.json`; first automatic run seeds current items.

## Gotchas

- `.env` has real secrets. Do not print the token.
- Server Members Intent is not required by default; avoid enabling `intents.members` unless it is also enabled in Discord Developer Portal, or the bot may fail to start.
- `bot.py` has mojibake comments/strings; avoid broad encoding rewrites.
- `templates/index.html` is UTF-8 and should stay that way.
- `rg`, `git`, `python`, or `py` may be unavailable; use PowerShell/bundled runtimes if needed.
- Bundled Python can verify syntax but may not have `discord.py`/`flask`.
- Discord may take several minutes to refresh removed/changed slash commands.

## Verify

```powershell
& 'C:\Users\dongb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile bot.py web.py
```

```powershell
& 'C:\Users\dongb\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' -e "const fs=require('fs');const s=fs.readFileSync('templates/index.html','utf8');const m=s.match(/<script>([\s\S]*)<\/script>/);new Function(m[1]);console.log('js syntax ok')"
```
