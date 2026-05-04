# Bot Discord

Bot Discord dùng để quản lý spam trap, xoá tin nhắn theo điều kiện, theo dõi patch/update game Steam và điều khiển qua dashboard web.

## Tính Năng Chính

- Dashboard web chạy bằng Flask, theme Discord, có sidebar 6 trang: Tổng quan (status + sparkline CPU/RAM + tác vụ nhanh), Cấu hình, Steam Watcher, Log gần đây, Ban log (lịch sử ban + tải file), Version. Save Config tự restart bot, log timestamp UTC+7.
- Slash command và text command cho Discord.
- Spam trap: gắn role nghi phạm, xoá tin nhắn, ban khi nghi phạm tiếp tục nhắn vào kênh bẫy; có bộ đếm "mít tơ bít đã ban" tự cập nhật trong `SUSPECT_CHANNEL_ID`.
- Ghi log mọi lượt ban (kể cả admin ban tay) vào thread `BAN_LOG_THREAD_ID` kèm thông tin audit log.
- Auto-delete: xoá embed/tin nhắn theo user ID và từ khoá cấu hình; có thể giới hạn theo category/loại trừ kênh.
- Steam watcher: theo dõi patch/update game bằng Steam Events.
- Quản lý danh sách game bằng lệnh `/game add`, `/game remove`, `/game list`, `/game help`.

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

Lưu ý: khi bấm Save Config trên dashboard, bot đang chạy sẽ tự được dừng và start lại để nạp `.env` mới.

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
/game help
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

Ghi chú:

- Các lệnh quản trị cần quyền `Manage Messages`.
- `/dlt` slash trả lời ephemeral (chỉ người gọi thấy).
- `/check` và `/game remove` slash có autocomplete theo bảng game.

## Spam Trap

Biến `.env` quan trọng:

```env
SPAM_TRAP_CHANNEL_ID=''
SPAM_TRAP_CHANNEL_ID_2=''
SUSPECT_CHANNEL_ID=''
SUSPECT_ROLE_ID=''
BAN_LOG_THREAD_ID=''
```

Cách hoạt động:

- Người nhắn vào kênh bẫy sẽ bị gắn role nghi phạm và tin nhắn bị xoá.
- Người nhắn vào `SUSPECT_CHANNEL_ID` cũng bị gắn role nghi phạm và tin nhắn bị xoá.
- Người đã có role nghi phạm mà nhắn vào kênh bẫy sẽ bị ban.
- Người có role trong `SPAM_TRAP_EXCLUDED_ROLE_IDS` được miễn trừ: tin nhắn ở kênh bẫy/nghi phạm vẫn bị xoá, nhưng **không** bị gắn role nghi phạm và **không** bị ban.
- Log ban gửi vào thread `BAN_LOG_THREAD_ID`. Nếu không gửi được, fallback sang `GENERAL_LOG_CHANNEL_ID`.
- Bot duy trì 1 message bộ đếm "Số mít tơ bít đã ban: N" trong `SUSPECT_CHANNEL_ID`, tự edit khi có ban mới.

## Ban Log Tự Động

Ngoài spam trap, bot còn lắng nghe sự kiện `on_member_ban`. Mỗi khi có người bị ban (kể cả admin ban tay), bot gửi embed "Búa Tạ Đã Vung 🔨" vào `BAN_LOG_THREAD_ID` kèm thông tin từ audit log (ai ban, lý do nếu có).

## Tin Nhắn Khởi Động

Đặt `STARTUP_CHANNEL_ID` để bot gửi tin "🟢 Hệ thống phòng chống Spam đã được khởi động..." mỗi lần online.

## Auto-Delete Embed

Bot xoá embed khi cả 3 điều kiện đúng:

- `message.author.id == TARGET_USER_ID`.
- Embed chứa ít nhất 1 keyword trong `TARGET_KEYWORDS` (so sánh lower-case).
- Nếu có `TARGET_CATEGORY_IDS`, kênh phải nằm trong danh sách đó.
- Nếu có `EXCLUDED_CHANNEL_IDS`, kênh không nằm trong danh sách loại trừ.

Lệnh `/dlt [limit]` quét chủ động mọi kênh trong `TARGET_CATEGORY_IDS` và xoá những tin của `TARGET_USER_ID` khớp keyword. Mặc định 100 tin/kênh, tối đa 500.

## Steam Watcher

Biến `.env` quan trọng:

```env
STEAMDB_PATCH_CHANNEL_ID=''
STEAMDB_APP_IDS=''
STEAMDB_PATCH_INTERVAL_HOURS='1'
STEAMDB_PATCH_SCHEDULE_HOURS='0,6,12,18'
STEAMDB_PATCH_MAJOR_ONLY='false'
STEAMDB_PATCH_LIMIT='25'
STEAM_WATCHER_MAX_AGE_DAYS='7'
```

Ghi chú:

- Watcher chỉ chạy khi có `STEAMDB_PATCH_CHANNEL_ID`.
- `STEAMDB_PATCH_INTERVAL_HOURS > 0`: chạy theo interval (giờ), clamp 1–168.
- `STEAMDB_PATCH_INTERVAL_HOURS = 0`: chạy theo các giờ trong `STEAMDB_PATCH_SCHEDULE_HOURS` (mặc định `0,6,12,18`).
- `STEAM_WATCHER_MAX_AGE_DAYS` lọc bỏ event cũ hơn N ngày (mặc định 7).
- Mỗi lần check chỉ đẩy tối đa 1 patch để tránh spam; phần còn lại được ghi nhớ.
- `STEAMDB_PATCH_MENTION_USER_ID` ping một người; `STEAMDB_PATCH_MENTION_USER_IDS` ping nhiều người, cách nhau bằng dấu phẩy.
- `STEAMDB_APP_IDS` hỗ trợ dạng `730,570` hoặc `730_Counter-Strike 2, 570_Dota 2`.
- `/game add <SteamAppID>` lấy tên game từ Steam Store, ghi vào `.env`, rồi reload cấu hình.
- Nếu bot chạy trên VPS, `/game add` cập nhật `.env` trên VPS, không cập nhật `.env` local.
- Bot dùng Steam Events để lấy REGULAR UPDATE/MAJOR UPDATE. Mapping `event_type` của Steam Partner: `12` = MAJOR UPDATE, `13` = REGULAR UPDATE. `STEAMDB_PATCH_MAJOR_ONLY=true` sẽ chỉ lọc `event_type=12`.

## Kiểm Tra

```bash
python3 -m py_compile bot.py web.py
```

Nếu có Node.js, có thể kiểm tra JavaScript dashboard:

```bash
node -e "const fs=require('fs');const s=fs.readFileSync('static/dashboard.js','utf8');new Function(s);console.log('js syntax ok')"
```
