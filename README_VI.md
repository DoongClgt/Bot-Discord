# Bot Discord

Bot Discord dùng để quản lý spam trap, xoá tin nhắn theo điều kiện, theo dõi patch/update game Steam và điều khiển qua dashboard web.

## Tính Năng Chính

- Dashboard web chạy bằng Flask.
- Slash command và text command cho Discord.
- Spam trap: gắn role nghi phạm, xoá tin nhắn, ban khi nghi phạm tiếp tục nhắn vào kênh bẫy.
- Auto-delete: xoá embed/tin nhắn theo user ID và từ khoá cấu hình.
- Steam watcher: theo dõi patch/update game bằng Steam Events.
- Quản lý danh sách game bằng lệnh `/game add`, `/game remove`, `/game list`.

## Cài Đặt Trên VPS

Dành cho Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone https://github.com/DoongClgt/Bot-Discord.git
cd Bot-Discord
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Điền giá trị thật vào `.env`, tối thiểu cần:

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
```

## Chạy Bot

Chạy bot Discord:

```bash
source .venv/bin/activate
python3 bot.py
```

Chạy dashboard ở terminal khác:

```bash
source .venv/bin/activate
python3 web.py
```

Hoặc chạy cả bot và dashboard bằng script VPS:

```bash
chmod +x deploy/start_vps.sh
./deploy/start_vps.sh
```

Dashboard mặc định:

```text
http://127.0.0.1:5000
```

## Cloudflare Tunnel

Nếu dùng Cloudflare Tunnel, giữ dashboard chạy local trên VPS:

```env
DASHBOARD_HOST='127.0.0.1'
DASHBOARD_PORT='5000'
DASHBOARD_PUBLIC_URL='https://bot.example.com'
```

Trong Cloudflare Tunnel, trỏ public hostname về:

```text
http://127.0.0.1:5000
```

Không nên mở trực tiếp port `5000` ra internet nếu dashboard chưa có lớp bảo vệ riêng.

## Lệnh Discord

Text command:

```text
/ping / /online / /status
/steamdbcheck / /patchcheck
/check [index|SteamAppID|tên game]
/dlt [limit]
/game list
/game add <SteamAppID>
/game remove <index|SteamAppID|tên game>
/refreshchannels / /rescanchannels
```

Slash command:

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

Các lệnh quản trị cần quyền `Manage Messages`.

## Spam Trap

Biến `.env` quan trọng:

```env
SPAM_TRAP_CHANNEL_ID=''
SPAM_TRAP_CHANNEL_ID_2=''
SUSPECT_CHANNEL_ID=''
SUSPECT_ROLE_NAME='Nghi Pham'
BAN_LOG_THREAD_ID=''
```

Cách hoạt động:

- Người nhắn vào kênh bẫy sẽ bị gắn role nghi phạm và tin nhắn bị xoá.
- Người nhắn vào `SUSPECT_CHANNEL_ID` cũng bị gắn role nghi phạm và tin nhắn bị xoá.
- Người đã có role nghi phạm mà nhắn vào kênh bẫy sẽ bị ban.
- Người có role trong `SPAM_TRAP_EXCLUDED_ROLE_IDS` sẽ được bỏ qua trong kênh bẫy và kênh nghi phạm.
- Log ban gửi vào thread `BAN_LOG_THREAD_ID`.

## Steam Watcher

Biến `.env` quan trọng:

```env
STEAMDB_PATCH_CHANNEL_ID=''
STEAMDB_APP_IDS=''
STEAMDB_PATCH_INTERVAL_HOURS='1'
STEAMDB_PATCH_MAJOR_ONLY='false'
STEAMDB_PATCH_LIMIT='25'
STEAM_WATCHER_MAX_AGE_DAYS='7'
```

Ghi chú:

- Watcher chỉ chạy khi có `STEAMDB_PATCH_CHANNEL_ID`.
- `STEAMDB_PATCH_MENTION_USER_ID` ping một người; `STEAMDB_PATCH_MENTION_USER_IDS` ping nhiều người, cách nhau bằng dấu phẩy.
- `STEAMDB_APP_IDS` hỗ trợ dạng `730,570` hoặc `730_Counter-Strike 2, 570_Dota 2`.
- `/game add <SteamAppID>` lấy tên game từ Steam Store, ghi vào `.env`, rồi reload cấu hình.
- Nếu bot chạy trên VPS, `/game add` cập nhật `.env` trên VPS, không cập nhật `.env` local.
- Bot dùng Steam Events để lấy REGULAR UPDATE/MAJOR UPDATE.

## Kiểm Tra

```bash
python3 -m py_compile bot.py web.py
```

Nếu có Node.js, có thể kiểm tra JavaScript dashboard:

```bash
node -e "const fs=require('fs');const s=fs.readFileSync('templates/index.html','utf8');const m=s.match(/<script>([\s\S]*)<\/script>/);new Function(m[1]);console.log('js syntax ok')"
```
