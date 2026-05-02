# Discord Bot

A Discord bot for moderation, spam-trap handling, Steam patch/update watching, and a small Flask dashboard.

Vietnamese setup guide: [README_VI.md](README_VI.md)

## Features

- Flask dashboard for status, config, logs, and manual actions.
- Discord slash commands and text fallback commands.
- Spam trap flow: assign suspect role, delete trap messages, and ban repeat suspects.
- Auto-delete messages/embeds by configured target user and keywords.
- Steam patch/update watcher using Steam Events.
- Manage watched Steam games with `/game add`, `/game remove`, and `/game list`.

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
STEAMDB_PATCH_CHANNEL_ID=''
STEAMDB_PATCH_MENTION_USER_ID=''
STEAMDB_PATCH_MENTION_USER_IDS=''
STEAMDB_APP_IDS=''
SPAM_TRAP_EXCLUDED_ROLE_IDS=''
SUSPECT_CHANNEL_ID=''
SPAM_TRAP_CHANNEL_ID=''
SPAM_TRAP_CHANNEL_ID_2=''
BAN_LOG_THREAD_ID=''
DASHBOARD_HOST='127.0.0.1'
DASHBOARD_PORT='5000'
```

Do not commit `.env`; use `.env.example` as the public template.

## Commands

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

Admin commands require `Manage Messages`.

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
node -e "const fs=require('fs');const s=fs.readFileSync('templates/index.html','utf8');const m=s.match(/<script>([\s\S]*)<\/script>/);new Function(m[1]);console.log('js syntax ok')"
```
