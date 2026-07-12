# Bot Discord

Bot Discord dùng để quản lý spam trap, xoá tin nhắn theo điều kiện, theo dõi patch/update game Steam và điều khiển qua dashboard web.

## Tính Năng Chính

- Dashboard web chạy bằng Flask, theme Discord, có sidebar: Tổng quan (status + sparkline CPU/RAM + tác vụ nhanh), Cấu hình, Steam Watcher, Tải TikTok (tải video/ảnh về máy), Log gần đây, Ban log (lịch sử ban + tải file), Tickets, Version. Save Config tự restart bot, log timestamp UTC+7.
- Slash command và text command cho Discord.
- Spam trap: ai chat vào kênh bẫy là bị ban luôn (role miễn trừ chỉ bị xoá tin nhắn), có bộ đếm "mít tơ bít đã ban" tự cập nhật trong cả 2 kênh bẫy.
- Ghi log mọi lượt ban (kể cả admin ban tay) vào thread `BAN_LOG_THREAD_ID` kèm thông tin audit log.
- Auto-delete: xoá embed/tin nhắn theo user ID và từ khoá cấu hình; có thể giới hạn theo category/loại trừ kênh.
- Tự động cấp role cho thành viên mới khi vào server (nếu đã có role thì bỏ qua).
- Steam watcher: theo dõi patch/update game bằng Steam Events.
- Quản lý danh sách game bằng lệnh `/game add`, `/game remove`, `/game list`, `/game help`.
- Tải video/ảnh TikTok & Douyin không logo **qua dashboard** (trang "Tải TikTok"). *(Lệnh `/tiktok` trong Discord hiện đã tắt.)*

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
# Kênh bẫy: nhiều ID cách nhau bằng dấu phẩy. Thêm/bớt được ngay trên dashboard.
SPAM_TRAP_CHANNEL_IDS=''
SPAM_TRAP_EXCLUDED_ROLE_IDS=''
SPAM_TRAP_BAN_DELETE_SECONDS='3600'

# Log channels
BAN_LOG_THREAD_ID=''
STARTUP_CHANNEL_ID=''
GENERAL_LOG_CHANNEL_ID=''

# Auto role cho thành viên mới (để trống = tắt)
NEW_MEMBER_ROLE_ID=''
# Công tắc bật/tắt handler on_member_join mà không cần xóa Role ID ở trên
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

### Chạy bằng systemd (khuyến nghị cho production)

`start_vps.sh` chạy bằng `nohup` không chống được việc lỡ khởi động 2 lần → **2 tiến trình bot chạy song song sẽ ban/ghi log trùng** (idempotency guard chỉ chống trùng trong 1 tiến trình). Dùng systemd để đảm bảo **chỉ 1 instance**:

```bash
sudo bash deploy/install_systemd.sh
# hoặc chỉ định user chạy service:
sudo RUN_USER=youruser bash deploy/install_systemd.sh
```

Script tự dò `PROJECT_DIR`/user, kill tiến trình pid cũ, ghi 2 unit `bot-discord-bot.service` + `bot-discord-dashboard.service`, cài polkit rule (để dashboard/deploy điều khiển service không cần sudo), rồi `enable --now`. Sau đó:

```bash
sudo systemctl status bot-discord-bot bot-discord-dashboard
journalctl -u bot-discord-bot -f
```

Khi đã dùng systemd thì **không chạy `start_vps.sh` nữa** (sẽ tạo tiến trình trùng). `deploy_from_webhook.sh` tự nhận biết: nếu có service systemd thì restart qua systemd, không thì fallback cách cũ.

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
/synccounter / /recount / /recountban
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
/synccounter
/game list
/game add <app_id>
/game remove <game>
/game help
/ticket_panel
```

Ghi chú:

- Các lệnh quản trị cần quyền `Manage Messages`.
- `/dlt` slash trả lời ephemeral (chỉ người gọi thấy).
- `/check` và `/game remove` slash có autocomplete theo bảng game.

## Tải TikTok / Douyin (qua dashboard)

- Mở trang **Tải TikTok** ở sidebar, dán link TikTok hoặc Douyin rồi bấm **Lấy video** — dashboard hiện preview (ảnh bìa, tiêu đề, tác giả) và nút tải video/ảnh **không logo về thẳng máy** qua trình duyệt. API: `POST /api/tiktok/resolve`, `GET /api/tiktok/download`.
- Dùng API `tikwm.com` — không cần cài thêm gì (không yt-dlp/ffmpeg).
- File tải về đặt tên theo **tiêu đề clip + ID video** (vd `Tiêu đề clip_7660736561704717620.mp4`) để không bị trùng.
- Link Douyin: tikwm không hỗ trợ nên tự parse thẳng từ trang share Douyin, lấy bản không logo.
- **Lệnh `/tiktok` trong Discord đã tắt** (không import `downloader.py` trong `bot.py`). Muốn bật lại: bỏ comment dòng `import downloader` rồi restart bot.

## Spam Trap

Biến `.env` quan trọng:

```env
SPAM_TRAP_CHANNEL_IDS=''
SPAM_TRAP_EXCLUDED_ROLE_IDS=''
SPAM_TRAP_BAN_DELETE_SECONDS='3600'
BAN_LOG_THREAD_ID=''
```

Cách hoạt động:

- Kênh bẫy khai báo ở `SPAM_TRAP_CHANNEL_IDS` (nhiều ID cách nhau bằng dấu phẩy, không giới hạn số kênh). Trên dashboard, tab **Spam trap** có ô chọn kênh: gõ tên kênh để thêm, bấm `×` để bỏ, rồi **Lưu và restart bot**. Hai biến cũ `SPAM_TRAP_CHANNEL_ID` / `SPAM_TRAP_CHANNEL_ID_2` vẫn được đọc nếu `.env` cũ còn, và sẽ tự gộp vào biến mới ở lần lưu đầu tiên.
- Ai nhắn vào kênh bẫy là **bị ban luôn** (kèm xoá tin nhắn). Không còn role/kênh nghi phạm.
- Khi ban, Discord xoá luôn tin nhắn của người đó **ở mọi kênh** trong khoảng `SPAM_TRAP_BAN_DELETE_SECONDS` giây gần nhất (mặc định 3600 = 1 tiếng, tối đa 604800). Nhờ vậy tin cũ ở các kênh ngoài cũng bị dọn, không chỉ tin vừa gửi.
- Người có role trong `SPAM_TRAP_EXCLUDED_ROLE_IDS` được miễn trừ: tin nhắn ở kênh bẫy vẫn bị xoá nhưng **không** bị ban.
- Log ban gửi vào thread `BAN_LOG_THREAD_ID`. Nếu không gửi được, fallback sang `GENERAL_LOG_CHANNEL_ID`.
- Mỗi kênh bẫy có 1 message bộ đếm "Số mít tơ bít đã ban: N" tự edit khi có ban mới.
- Nếu số đếm bị lệch (vd state bị reset), dùng lệnh `synccounter` (prefix hoặc slash, cần quyền `Manage Messages`) hoặc nút **"Cập nhật số đếm ban"** trên dashboard để tính lại từ `ban_log.jsonl` và cập nhật message.
- Có chống trùng (idempotency) theo `(guild_id, user_id)` để tránh ghi 2 dòng log nếu gateway gửi MESSAGE_CREATE 2 lần cho cùng 1 tin.

## Ban Log Tự Động

Ngoài spam trap, bot còn lắng nghe sự kiện `on_member_ban`. Mỗi khi có người bị ban (kể cả admin ban tay), bot gửi embed "Búa Tạ Đã Vung 🔨" vào `BAN_LOG_THREAD_ID` kèm thông tin từ audit log (ai ban, lý do nếu có).

Admin ban tay cũng được ghi vào `data/ban_log.jsonl` và hiện trên trang **Ban log** của dashboard, cột **Nguồn** ghi `Admin` + tên người ban (ban từ bẫy ghi `Spam trap` + tên bot). Mọi dòng đều lưu `banned_by_id`, `banned_by_name`, `banned_by_display_name`. Ghi chú:

- Ban do chính bot thực hiện không bị ghi 2 lần.
- Muốn biết ai ban, bot cần quyền **View Audit Log**; thiếu quyền thì vẫn ghi log nhưng cột Nguồn hiện "không rõ ai ban".
- Bộ đếm "Số mít tơ bít đã ban" trong kênh bẫy **không** tính ban của admin, kể cả khi bấm "Cập nhật số đếm ban".

## Tin Nhắn Khởi Động

Đặt `STARTUP_CHANNEL_ID` để bot gửi tin "🟢 Hệ thống phòng chống Spam đã được khởi động..." mỗi lần online.

## Auto Role Cho Thành Viên Mới

Đặt `NEW_MEMBER_ROLE_ID` để bot tự cấp role này cho ai vừa join server.

- Bỏ qua bot và những user đã có role đó (idempotent).
- Bot phải có quyền `Manage Roles` và role của bot phải nằm **cao hơn** role cần cấp trong danh sách role của server.
- Để trống biến này là tắt feature. Yêu cầu intent `Server Members` đã được bật trong Discord Developer Portal.
- `AUTO_ROLE_ON_JOIN_ENABLED` (mặc định `true`) là công tắc bật/tắt handler join mà không cần xóa Role ID. Đặt `false`/`0`/`off`/`no` (hoặc để trống) để tắt.
- Log ghi vào `bot_events.log` với event `auto_role` (thành công, không tìm thấy role, Forbidden, HTTP error).
- Dashboard: chọn **Bật/Tắt** ở mục "Tự cấp role khi member join" và nhập Role ID ở "Role tự cấp cho thành viên mới", rồi bấm Lưu — bot sẽ tự restart và áp dụng. Tên role được resolve hiển thị ngay dưới ô nhập.

## Hệ thống Ticket

Lấy cảm hứng từ Ticket Tool / Tickety. User bấm button trên panel để mở channel riêng, staff trả lời trong đó; khi đóng bot lưu transcript dạng `.txt` và xóa channel.

- `/ticket_panel` (slash, cần quyền `Manage Server`): post một embed kèm button "🎫 Tạo ticket" vào channel hiện tại. Có thể chạy nhiều lần. Panel cũ vẫn hoạt động sau khi bot restart nhờ persistent view.
- Tiêu đề + nội dung embed panel có thể chỉnh qua `TICKET_PANEL_TITLE` và `TICKET_PANEL_DESCRIPTION` (markdown + xuống dòng OK). Để trống = dùng mặc định. Sửa trên dashboard ở tab Cấu hình → Ticket; bot tự restart áp dụng, nhưng panel đã post trước đó giữ text cũ — phải chạy lại `/ticket_panel` để post panel mới.
- User bấm button → bot tạo private text channel `NNNN-<username>` dưới `TICKET_CATEGORY_ID` (category **chờ xác nhận**). Chỉ user mở ticket, bot, và mọi role trong `TICKET_SUPPORT_ROLE_IDS` (cách nhau bằng dấu phẩy) được thấy; `@everyone` bị deny view. Mỗi user chỉ mở được 1 ticket cùng lúc — bấm lại sẽ trỏ về channel sẵn có.
- Trong channel ticket: bot **chỉ mention người mở ticket** (không ping support role — staff tự thấy channel qua category chờ xác nhận) và post 3 button persistent (chỉ support được dùng): **✅ Xác nhận**, **🔒 Close**, **🗑️ Delete**.
- **Xác nhận** → ghi `confirmed_by`/`confirmed_at`, đổi tên channel thành `NNNN-<staff>-<user>` (lowercase, lọc về `[a-z0-9-]`, max 100 ký tự), và nếu có `TICKET_CONFIRMED_CATEGORY_ID` thì bot tự move channel sang category đó qua `channel.edit(name=..., category=...)`. Overwrite trên channel được giữ nguyên (không sync_permissions), độ riêng tư không đổi. Chỉ xác nhận được 1 lần. Lưu ý rate limit Discord: 2 lần đổi tên / 10 phút / channel.
- **Close** → ghi `closed_by`/`closed_at` và nếu có `TICKET_CLOSED_CATEGORY_ID` thì move channel sang category archive. Channel KHÔNG bị xóa, KHÔNG tạo transcript. State vẫn còn trong `data/tickets.json` cho đến khi Delete.
- **Delete** → confirm ephemeral → ghi `deleted_by`/`deleted_at`, build transcript, gửi vào log channel rồi xóa channel. Đây là action **duy nhất** tạo file transcript.
- Quy trình tạo transcript (chỉ khi bấm **Delete**):
  - Bot dump toàn bộ history thành transcript `.txt` (timestamp, tác giả, content, embed, attachment URL).
  - Lưu vào `data/transcripts/ticket-NNNN-<channelId>.txt` và append 1 dòng vào `data/transcripts_index.jsonl`.
  - Nếu có `TICKET_LOG_CHANNEL_ID`: gửi embed tóm tắt + file transcript vào kênh đó.
  - Đợi 3s rồi xóa channel.
- User xóa channel thủ công (không qua button) → handler `on_guild_channel_delete` tự dọn entry trong `data/tickets.json` và log `ticket_orphan`.
- Counter ticket persist trong `data/tickets_counter.txt`, tăng đơn điệu qua các lần restart.
- Quyền bot cần có: `Manage Channels`, `Manage Messages`, `View Channel`, `Send Messages`, `Read Message History`, `Embed Links`, `Attach Files`.
- Dashboard: tab **Tickets** liệt kê toàn bộ transcript đã đóng. Mỗi dòng có button "Tải .txt", header có thêm button "Tải tất cả (.zip)" — bot zip toàn bộ `data/transcripts/*.txt` + `transcripts_index.jsonl` in-memory rồi stream xuống. API: `GET /api/tickets/transcripts`, `GET /api/tickets/transcripts/<filename>`, `GET /api/tickets/transcripts/download_all`. 3 ID config hiển thị dạng read-only chip trong tab Cấu hình mục "Ticket system".
- Event log: `ticket_open`, `ticket_confirm`, `ticket_close`, `ticket_delete`, `ticket_orphan`.

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
STEAMDB_PATCH_INTERVAL_MINUTES=''
STEAMDB_PATCH_SCHEDULE_HOURS='0,6,12,18'
STEAMDB_PATCH_LIMIT='25'
STEAM_WATCHER_MAX_AGE_DAYS='7'
```

Ghi chú:

- Watcher chỉ chạy khi có `STEAMDB_PATCH_CHANNEL_ID`.
- `STEAMDB_PATCH_INTERVAL_MINUTES > 0`: chạy theo interval (phút), clamp 1–1440, **ưu tiên cao nhất** (vd `30` → 00:00, 00:30, 01:00,...). Lịch cũng align từ **0h mỗi ngày**.
- `STEAMDB_PATCH_INTERVAL_HOURS > 0` (khi `STEAMDB_PATCH_INTERVAL_MINUTES` = 0/rỗng): chạy theo interval (giờ), clamp 1–168. Lịch tính từ **0h mỗi ngày**, không phải từ lúc bot online (vd interval=1 → 00:00, 01:00, 02:00,...; interval=3 → 00:00, 03:00, 06:00,...).
- Cả hai = 0: chạy theo các giờ trong `STEAMDB_PATCH_SCHEDULE_HOURS` (mặc định `0,6,12,18`).
- Dashboard trang "Steam Watcher" chỉnh interval **theo phút** (`STEAMDB_PATCH_INTERVAL_MINUTES`); khi lưu sẽ tự xoá `STEAMDB_PATCH_INTERVAL_HOURS` cũ. Muốn dùng interval theo giờ thì sửa tay trong `.env`.
- `STEAM_WATCHER_MAX_AGE_DAYS` lọc bỏ event cũ hơn N ngày (mặc định 7).
- Mỗi lần check chỉ đẩy tối đa 1 patch để tránh spam; phần còn lại được ghi nhớ.
- `STEAMDB_PATCH_MENTION_USER_ID` ping một người; `STEAMDB_PATCH_MENTION_USER_IDS` ping nhiều người, cách nhau bằng dấu phẩy.
- `STEAMDB_APP_IDS` hỗ trợ dạng `730,570` hoặc `730_Counter-Strike 2, 570_Dota 2`.
- `/game add <SteamAppID>` lấy tên game từ Steam Store, ghi vào `.env`, rồi reload cấu hình.
- Nếu bot chạy trên VPS, `/game add` cập nhật `.env` trên VPS, không cập nhật `.env` local.
- Bot dùng Steam Events để lấy update. Mapping `event_type` của Steam Partner: `12` = SMALL UPDATE / PATCH NOTES, `13` = REGULAR UPDATE, `14` = MAJOR UPDATE. Bot cũng đọc thêm `event_type=28` nếu tiêu đề giống patch/update notes.

## Kiểm Tra

```bash
python3 -m py_compile bot.py core.py moderation.py steam.py tickets.py web.py
```

Nếu có Node.js, có thể kiểm tra JavaScript dashboard:

```bash
node -e "const fs=require('fs');const s=fs.readFileSync('static/dashboard.js','utf8');new Function(s);console.log('js syntax ok')"
```
