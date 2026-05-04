import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser
from discord.ext import tasks
from dotenv import load_dotenv
import dotenv

# Tải cấu hình từ file .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Lấy từ khóa cấm từ .env
TARGET_KEYWORDS_RAW = os.getenv('TARGET_KEYWORDS', 'bad word usage, too many infractions')
TARGET_KEYWORDS = [kw.strip().lower() for kw in TARGET_KEYWORDS_RAW.split(',') if kw.strip()]

def parse_int_set(raw_value):
    return {
        int(item.strip())
        for item in str(raw_value or '').split(',')
        if item.strip().isdigit()
    }

# ID của người hoặc bot mà bạn muốn xóa tin nhắn (lấy từ tùy chọn .env)
TARGET_USER_ID = int(os.getenv('TARGET_USER_ID', 0))

# Lấy danh sách ID danh mục (category) cần xóa tin nhắn (cách nhau bởi dấu phẩy)
category_ids_str = os.getenv('TARGET_CATEGORY_IDS', '')
TARGET_CATEGORY_IDS = [int(cat_id.strip()) for cat_id in category_ids_str.split(',')] if category_ids_str else []

# Lấy danh sách ID kênh (channel) muốn loại trừ, không xóa tin nhắn ở đây
excluded_channel_ids_str = os.getenv('EXCLUDED_CHANNEL_IDS', '')
EXCLUDED_CHANNEL_IDS = [int(ch_id.strip()) for ch_id in excluded_channel_ids_str.split(',')] if excluded_channel_ids_str else []

SUSPECT_CHANNEL_ID_STR = os.getenv('SUSPECT_CHANNEL_ID', '')
SUSPECT_CHANNEL_ID = int(SUSPECT_CHANNEL_ID_STR) if SUSPECT_CHANNEL_ID_STR.isdigit() else 0
SPAM_TRAP_CHANNEL_ID_STR = os.getenv('SPAM_TRAP_CHANNEL_ID', '')
SPAM_TRAP_CHANNEL_ID = int(SPAM_TRAP_CHANNEL_ID_STR) if SPAM_TRAP_CHANNEL_ID_STR.isdigit() else 0
SPAM_TRAP_CHANNEL_ID_2_STR = os.getenv('SPAM_TRAP_CHANNEL_ID_2', '')
SPAM_TRAP_CHANNEL_ID_2 = int(SPAM_TRAP_CHANNEL_ID_2_STR) if SPAM_TRAP_CHANNEL_ID_2_STR.isdigit() else 0
SPAM_TRAP_CHANNEL_IDS = {channel_id for channel_id in (SPAM_TRAP_CHANNEL_ID, SPAM_TRAP_CHANNEL_ID_2) if channel_id}
SPAM_TRAP_EXCLUDED_ROLE_IDS = parse_int_set(os.getenv('SPAM_TRAP_EXCLUDED_ROLE_IDS', ''))
SUSPECT_ROLE_ID_STR = os.getenv('SUSPECT_ROLE_ID', '')
SUSPECT_ROLE_ID = int(SUSPECT_ROLE_ID_STR) if SUSPECT_ROLE_ID_STR.isdigit() else 0

BAN_LOG_THREAD_ID_STR = os.getenv('BAN_LOG_THREAD_ID', '')
BAN_LOG_THREAD_ID = int(BAN_LOG_THREAD_ID_STR) if BAN_LOG_THREAD_ID_STR.isdigit() else 0

DELETE_LOG_THREAD_ID_STR = os.getenv('DELETE_LOG_THREAD_ID', '')
DELETE_LOG_THREAD_ID = int(DELETE_LOG_THREAD_ID_STR) if DELETE_LOG_THREAD_ID_STR.isdigit() else 0

STARTUP_CHANNEL_ID_STR = os.getenv('STARTUP_CHANNEL_ID', '')
STARTUP_CHANNEL_ID = int(STARTUP_CHANNEL_ID_STR) if STARTUP_CHANNEL_ID_STR.isdigit() else 0

GENERAL_LOG_CHANNEL_ID_STR = os.getenv('GENERAL_LOG_CHANNEL_ID', '')
GENERAL_LOG_CHANNEL_ID = int(GENERAL_LOG_CHANNEL_ID_STR) if GENERAL_LOG_CHANNEL_ID_STR.isdigit() else 0

STEAMDB_PATCH_CHANNEL_ID_STR = os.getenv('STEAMDB_PATCH_CHANNEL_ID', '')
STEAMDB_PATCH_CHANNEL_ID = int(STEAMDB_PATCH_CHANNEL_ID_STR) if STEAMDB_PATCH_CHANNEL_ID_STR.isdigit() else 0
STEAMDB_PATCH_MENTION_USER_ID_STR = os.getenv('STEAMDB_PATCH_MENTION_USER_ID', '')
STEAMDB_PATCH_MENTION_USER_IDS_RAW = os.getenv('STEAMDB_PATCH_MENTION_USER_IDS', '')
STEAMDB_PATCH_MENTION_USER_IDS = [
    user_id for user_id in dict.fromkeys(
        item.strip()
        for item in f"{STEAMDB_PATCH_MENTION_USER_ID_STR},{STEAMDB_PATCH_MENTION_USER_IDS_RAW}".split(',')
    )
    if user_id.isdigit()
]
STEAMDB_APP_IDS_RAW = os.getenv('STEAMDB_APP_IDS', '')
def parse_steam_app_entries(raw_value):
    entries = []
    for item in raw_value.split(','):
        value = item.strip().strip("'").strip('"')
        if not value:
            continue
        match = re.match(r'^(\d+)(?:[_:\-|]\s*(.+))?$', value)
        if not match:
            continue
        app_id = match.group(1)
        name = (match.group(2) or f"Steam App {app_id}").strip()
        entries.append({"id": app_id, "name": name, "label": f"{app_id}_{name}"})
    return entries

STEAM_APP_ENTRIES = parse_steam_app_entries(STEAMDB_APP_IDS_RAW)
STEAMDB_APP_IDS = {entry["id"] for entry in STEAM_APP_ENTRIES}
STEAM_APP_NAMES = {entry["id"]: entry["name"] for entry in STEAM_APP_ENTRIES}
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
STEAMDB_PATCH_INTERVAL_HOURS_RAW = os.getenv('STEAMDB_PATCH_INTERVAL_HOURS', '').strip()
STEAMDB_PATCH_INTERVAL_HOURS = (
    int(STEAMDB_PATCH_INTERVAL_HOURS_RAW)
    if STEAMDB_PATCH_INTERVAL_HOURS_RAW.isdigit()
    else 0
)
STEAMDB_PATCH_INTERVAL_HOURS = min(max(STEAMDB_PATCH_INTERVAL_HOURS, 0), 168)
STEAMDB_PATCH_SCHEDULE_HOURS_RAW = os.getenv('STEAMDB_PATCH_SCHEDULE_HOURS', '0,6,12,18')
STEAMDB_PATCH_SCHEDULE_HOURS = sorted({
    int(hour.strip()) for hour in STEAMDB_PATCH_SCHEDULE_HOURS_RAW.split(',')
    if hour.strip().isdigit() and 0 <= int(hour.strip()) <= 23
}) or [0, 6, 12, 18]
STEAMDB_PATCH_LIMIT_STR = os.getenv('STEAMDB_PATCH_LIMIT', '25')
STEAMDB_PATCH_LIMIT = int(STEAMDB_PATCH_LIMIT_STR) if STEAMDB_PATCH_LIMIT_STR.isdigit() else 25
STEAMDB_PATCH_LIMIT = min(max(STEAMDB_PATCH_LIMIT, 5), 100)
STEAM_WATCHER_MAX_AGE_DAYS_STR = os.getenv('STEAM_WATCHER_MAX_AGE_DAYS', '7')
STEAM_WATCHER_MAX_AGE_DAYS = int(STEAM_WATCHER_MAX_AGE_DAYS_STR) if STEAM_WATCHER_MAX_AGE_DAYS_STR.isdigit() else 7
STEAM_WATCHER_MAX_AGE_DAYS = min(max(STEAM_WATCHER_MAX_AGE_DAYS, 1), 365)
STEAM_HTTP_TIMEOUT = 8
RECENT_CHECK_TIMEOUT = 20
STEAM_WATCHER_SEND_LIMIT = 1
STEAM_RECENT_PATCH_CHECK_COUNT = 20
STEAM_EVENT_TYPE_LABELS = {
    12: "SMALL UPDATE / PATCH NOTES",
    13: "REGULAR UPDATE",
    14: "MAJOR UPDATE",
}

def safe_http_url(url, fallback=None):
    value = str(url or '').strip()
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/:@!$&'()*+=;")
        query = urllib.parse.quote(urllib.parse.unquote(parsed.query), safe="=&?/:@!$'()*+;")
        fragment = urllib.parse.quote(urllib.parse.unquote(parsed.fragment), safe="=&?/:@!$'()*+;")
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, query, fragment))
    return fallback

def format_utc7_timestamp(timestamp):
    if not isinstance(timestamp, int):
        return ""
    dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
    dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
    return dt.strftime("%d-%m-%Y %H:%M UTC+7")

def steam_watcher_cutoff_ts():
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=STEAM_WATCHER_MAX_AGE_DAYS)
    return int(cutoff.timestamp())

def strip_steam_bbcode(value):
    text = unescape(str(value or ""))
    text = re.sub(r'\[/?(?:p|h\d|b|i|u|list|olist|quote|code|c)(?:=[^\]]*)?\]', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\[\*\]', '- ', text)
    text = re.sub(r'\[/\*\]', ' ', text)
    text = re.sub(r'\[url=[^\]]+\]([^\[]+)\[/url\]', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\[[^\]]+\]', ' ', text)
    return ' '.join(text.split())

def first_localized_text(values):
    if isinstance(values, list):
        for value in values:
            if isinstance(value, str) and value.strip():
                return strip_steam_bbcode(value)
    if isinstance(values, str) and values.strip():
        return strip_steam_bbcode(values)
    return ""

def steam_event_type_filter():
    return "12,13,14"

def steam_event_url(app_id, event_gid):
    return f"https://store.steampowered.com/news/app/{app_id}/view/{event_gid}"

def steam_event_to_patch(app_id, event):
    event_gid = str(event.get("gid") or "").strip()
    if not event_gid:
        return None

    announcement = event.get("announcement_body") if isinstance(event.get("announcement_body"), dict) else {}
    title = event.get("event_name") or announcement.get("headline") or "Steam event"
    event_type = event.get("event_type")
    event_type_label = STEAM_EVENT_TYPE_LABELS.get(event_type, f"EVENT {event_type}")
    date_value = (
        event.get("rtime32_start_time")
        or announcement.get("posttime")
        or event.get("rtime_created")
    )

    summary = ""
    try:
        jsondata = _json.loads(event.get("jsondata") or "{}")
        summary = first_localized_text(jsondata.get("localized_summary"))
    except Exception:
        summary = ""
    if not summary:
        summary = strip_steam_bbcode(announcement.get("body"))[:900]

    build_id = event.get("build_id")
    return {
        "id": f"steamevent:{app_id}:{event_gid}",
        "app_id": str(app_id),
        "game": STEAM_APP_NAMES.get(str(app_id), f"Steam App {app_id}"),
        "title": str(title),
        "date": format_utc7_timestamp(date_value),
        "url": steam_event_url(app_id, event_gid),
        "app_url": f"https://store.steampowered.com/news/app/{app_id}",
        "source": f"Steam Events - {event_type_label}",
        "summary": summary,
        "event_type": event_type_label,
        "build_id": str(build_id) if build_id else "",
        "_sort_ts": date_value if isinstance(date_value, int) else 0,
    }

# Khởi tạo intents để bot có quyền đọc được tin nhắn trên server
intents = discord.Intents.default()
intents.message_content = True


# Khai báo bot
bot = commands.Bot(command_prefix='/', intents=intents)
slash_commands_synced = False

def has_violating_words(message: discord.Message) -> bool:
    """Hàm dùng chung để kiểm tra xem một tin nhắn nhúng (embed) có chứa từ khoá cấm hay không."""
    if not getattr(message, 'embeds', None):
        return False
    
    for embed in message.embeds:
        text_to_check = [
            embed.title,
            embed.description,
            embed.author.name if embed.author else None,
            embed.footer.text if embed.footer else None
        ]
        
        for field in embed.fields:
            text_to_check.extend([field.name, field.value])
            
        valid_texts = [str(text).lower() for text in text_to_check if text]
        if any(any(t in text for t in TARGET_KEYWORDS) for text in valid_texts):
            return True
            
    return False

def collect_message_text(message: discord.Message, include_content: bool = False) -> list[str]:
    texts = []
    if include_content and getattr(message, 'content', None):
        texts.append(message.content)

    for embed in getattr(message, 'embeds', []) or []:
        texts.extend([
            embed.title,
            embed.description,
            embed.author.name if embed.author else None,
            embed.footer.text if embed.footer else None,
        ])
        for field in embed.fields:
            texts.extend([field.name, field.value])
    return [str(text).lower() for text in texts if text]

def message_has_target_keywords(message: discord.Message, include_content: bool = False) -> bool:
    if not TARGET_KEYWORDS:
        return False
    return any(
        keyword in text
        for text in collect_message_text(message, include_content=include_content)
        for keyword in TARGET_KEYWORDS
    )

async def delete_recent_target_keyword_messages(channel, limit: int = 100):
    if not TARGET_USER_ID:
        return 0, 0, "Chua cau hinh TARGET_USER_ID."
    if not TARGET_KEYWORDS:
        return 0, 0, "Chua cau hinh TARGET_KEYWORDS."
    if not hasattr(channel, 'history'):
        return 0, 0, "Kenh nay khong ho tro doc lich su tin nhan."

    limit = max(1, min(int(limit or 100), 500))
    scanned = 0
    deleted = 0
    failed = 0

    async for msg in channel.history(limit=limit):
        scanned += 1
        if msg.author.id != TARGET_USER_ID:
            continue
        if not message_has_target_keywords(msg, include_content=True):
            continue
        try:
            await msg.delete()
            deleted += 1
            await asyncio.sleep(0.2)
        except (discord.Forbidden, discord.HTTPException):
            failed += 1

    if failed:
        return scanned, deleted, f"Da quet {scanned} tin, xoa {deleted} tin, loi {failed} tin."
    return scanned, deleted, f"Da quet {scanned} tin gan nhat va xoa {deleted} tin vi pham cua TARGET_USER_ID."

def get_dlt_channels(guild: discord.Guild):
    if not TARGET_CATEGORY_IDS:
        return []

    channels = []
    for channel in guild.text_channels:
        if channel.category_id not in TARGET_CATEGORY_IDS:
            continue
        if EXCLUDED_CHANNEL_IDS and channel.id in EXCLUDED_CHANNEL_IDS:
            continue
        channels.append(channel)
        for thread in channel.threads:
            channels.append(thread)
    return channels

async def delete_target_keyword_messages_in_categories(guild: discord.Guild, limit: int = 100):
    if not guild:
        log_event("dlt", "Lenh /dlt duoc goi ngoai server.", "warn")
        return "Lenh nay chi dung duoc trong server."
    if not TARGET_CATEGORY_IDS:
        log_event("dlt", "Chua cau hinh TARGET_CATEGORY_IDS.", "warn")
        return "Chua cau hinh TARGET_CATEGORY_IDS de quet danh muc ap dung."

    channels = get_dlt_channels(guild)
    if not channels:
        log_event("dlt", "Khong tim thay kenh nao trong TARGET_CATEGORY_IDS.", "warn")
        return "Khong tim thay kenh nao trong TARGET_CATEGORY_IDS."

    limit = max(1, min(int(limit or 100), 500))
    total_scanned = 0
    total_deleted = 0
    details = []

    for channel in channels:
        scanned, deleted, _ = await delete_recent_target_keyword_messages(channel, limit)
        total_scanned += scanned
        total_deleted += deleted
        if deleted:
            details.append(f"{getattr(channel, 'mention', channel.name)}: {deleted}")
        await asyncio.sleep(0.3)

    result = (
        f"Da quet {len(channels)} kenh/thread trong danh muc ap dung, "
        f"{limit} tin moi nhat moi kenh. Da xoa {total_deleted}/{total_scanned} tin da quet."
    )
    if details:
        result += "\n" + "\n".join(details[:10])
        if len(details) > 10:
            result += f"\n... va {len(details) - 10} kenh/thread khac."
    log_event("dlt", f"Quet {len(channels)} kenh/thread, xoa {total_deleted}/{total_scanned} tin.")
    return result[:1900]

async def send_general_log(guild, log_content):
    if GENERAL_LOG_CHANNEL_ID:
        channel = bot.get_channel(GENERAL_LOG_CHANNEL_ID)
        if channel:
            try:
                await channel.send(log_content)
            except discord.Forbidden:
                pass

async def send_configured_ban_log(guild, log_content):
    log_channel = None
    if BAN_LOG_THREAD_ID:
        log_channel = bot.get_channel(BAN_LOG_THREAD_ID)
        if not log_channel:
            try:
                log_channel = await guild.fetch_channel(BAN_LOG_THREAD_ID)
            except Exception:
                log_channel = None

    if log_channel:
        try:
            await log_channel.send(log_content)
            return
        except discord.Forbidden:
            pass
    await send_general_log(guild, log_content)

async def get_or_create_suspect_role(guild: discord.Guild):
    if not SUSPECT_ROLE_ID:
        return None, "Chua cau hinh SUSPECT_ROLE_ID trong .env."
    role = guild.get_role(SUSPECT_ROLE_ID)
    if role:
        return role, None
    return None, f"Khong tim thay role nghi pham co ID {SUSPECT_ROLE_ID} trong guild."

async def sync_spam_trap_ban_counter(guild: discord.Guild, increment: bool = False):
    state = load_spam_trap_state()
    current_count = int(state.get("ban_count", 0) or 0)
    state["ban_count"] = current_count + 1 if increment else current_count
    message_text = f"Số mít tơ bít đã ban: {state['ban_count']}"
    channel = guild.get_channel(SUSPECT_CHANNEL_ID) or bot.get_channel(SUSPECT_CHANNEL_ID)
    if not channel:
        try:
            channel = await guild.fetch_channel(SUSPECT_CHANNEL_ID)
        except Exception:
            channel = None
    if not channel:
        save_spam_trap_state(state)
        return

    message_id = int(state.get("counter_message_id") or 0)
    if message_id:
        try:
            counter_message = await channel.fetch_message(message_id)
            await counter_message.edit(content=message_text)
            save_spam_trap_state(state)
            return
        except Exception:
            state["counter_message_id"] = 0

    try:
        counter_message = await channel.send(message_text)
        state["counter_message_id"] = counter_message.id
    except discord.Forbidden:
        pass
    save_spam_trap_state(state)

async def update_spam_trap_ban_counter(guild: discord.Guild):
    await sync_spam_trap_ban_counter(guild, increment=True)

async def ensure_suspect_role(member: discord.Member, reason: str, log_source: str):
    role, error = await get_or_create_suspect_role(member.guild)
    had_role = bool(role and role in member.roles)
    if role and not had_role:
        try:
            await member.add_roles(role, reason=reason)
            log_event("spam_trap", f"Gan role nghi pham cho {member.id} tu {log_source}.")
        except discord.Forbidden:
            error = "Bot khong co quyen gan role nghi pham."
        except discord.HTTPException as e:
            error = f"Khong gan duoc role nghi pham: {e}"
    return role, had_role, error

async def ban_spam_trap_suspect(message: discord.Message, reason_text: str, audit_reason: str):
    try:
        await message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

    author = message.author
    guild = message.guild
    channel = message.channel
    roles_snapshot = []
    if isinstance(author, discord.Member):
        roles_snapshot = [
            {"id": str(r.id), "name": r.name}
            for r in author.roles
            if guild is None or r.id != guild.id
        ]
    parent_channel = channel.parent if isinstance(channel, discord.Thread) else None

    try:
        await message.guild.ban(
            message.author,
            reason=audit_reason,
            delete_message_seconds=60,
        )
        await update_spam_trap_ban_counter(message.guild)
        log_event("spam_trap_ban", f"Da ban {message.author.id}: {reason_text}")
        append_ban_log({
            "guild_id": str(guild.id) if guild else "",
            "guild_name": guild.name if guild else "",
            "user_id": str(author.id),
            "username": str(author),
            "display_name": getattr(author, "display_name", None) or str(author),
            "user_created_at": author.created_at.isoformat() if getattr(author, "created_at", None) else "",
            "joined_at": author.joined_at.isoformat() if getattr(author, "joined_at", None) else "",
            "roles_at_ban": roles_snapshot,
            "channel_id": str(channel.id) if channel else "",
            "channel_name": getattr(channel, "name", "") or "",
            "channel_type": str(getattr(channel, "type", "")),
            "parent_channel_id": str(parent_channel.id) if parent_channel else "",
            "parent_channel_name": parent_channel.name if parent_channel else "",
            "message_id": str(message.id),
            "message_content": (message.content or "")[:1000],
            "message_created_at": message.created_at.isoformat() if getattr(message, "created_at", None) else "",
            "reason_text": reason_text,
            "audit_reason": audit_reason,
        })
    except discord.Forbidden:
        await send_configured_ban_log(message.guild, f"Khong ban duoc {message.author.mention}: bot thieu quyen Ban Members hoac role thap.")
    except discord.HTTPException as e:
        await send_configured_ban_log(message.guild, f"Khong ban duoc {message.author.mention}: {e}")

def has_spam_trap_excluded_role(member: discord.Member):
    if not SPAM_TRAP_EXCLUDED_ROLE_IDS:
        return False
    return any(role.id in SPAM_TRAP_EXCLUDED_ROLE_IDS for role in member.roles)

async def handle_spam_trap_message(message: discord.Message, actual_channel_id: int):
    if not isinstance(message.author, discord.Member) or not message.guild:
        return False

    is_spam_trap_channel = actual_channel_id in SPAM_TRAP_CHANNEL_IDS
    is_suspect_channel = bool(SUSPECT_CHANNEL_ID and actual_channel_id == SUSPECT_CHANNEL_ID)
    if (is_spam_trap_channel or is_suspect_channel) and has_spam_trap_excluded_role(message.author):
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        log_event("spam_trap", f"Xoa tin nhan tu {message.author.id}: co role mien tru, khong ban/gan role.")
        return True

    if is_spam_trap_channel:
        role, had_role, error = await ensure_suspect_role(
            message.author,
            "User sent a message in spam trap channel",
            "kenh bay",
        )

        if role and had_role:
            await ban_spam_trap_suspect(
                message,
                "Nghi pham da chat trong kenh bay.",
                "Spam trap: nghi pham chat trong kenh bay",
            )
            return True

        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        if error:
            await send_general_log(message.guild, f"Spam trap loi voi {message.author.mention}: {error}")
        return True

    if is_suspect_channel:
        role, had_role, error = await ensure_suspect_role(
            message.author,
            "User sent a message in suspect channel",
            "kenh nghi pham",
        )

        if role and had_role:
            await ban_spam_trap_suspect(
                message,
                "Nghi pham da chat trong kenh nghi pham.",
                "Spam trap: nghi pham chat trong kenh nghi pham",
            )
            return True

        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        if error:
            await send_general_log(message.guild, f"Spam trap loi voi {message.author.mention}: {error}")
        return True

    return False

# ===== Persistent data and IPC helpers =====
import json as _json

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

STEAMDB_PATCH_FILE = os.path.join(DATA_DIR, 'steamdb_patches.json')
CHANNELS_FILE = os.path.join(DATA_DIR, 'channels.json')
IPC_CMD_FILE = os.path.join(DATA_DIR, 'ipc_cmd.txt')
IPC_RESPONSE_FILE = os.path.join(DATA_DIR, 'ipc_response.txt')
BOT_EVENTS_FILE = os.path.join(DATA_DIR, 'bot_events.log')
BAN_LOG_FILE = os.path.join(DATA_DIR, 'ban_log.jsonl')
SPAM_TRAP_STATE_FILE = os.path.join(DATA_DIR, 'spam_trap_state.json')

def atomic_write_text(path, text):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(str(text))
    os.replace(tmp_path, path)

def atomic_write_json(path, data, indent=2):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        _json.dump(data, f, ensure_ascii=False, indent=indent)
    os.replace(tmp_path, path)

UTC7 = datetime.timezone(datetime.timedelta(hours=7))

def now_utc7_string():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(UTC7).strftime("%d-%m-%Y %H:%M:%S UTC+7")

def log_event(event, message, level="info", **extra):
    payload = {
        "time": now_utc7_string(),
        "level": level,
        "event": event,
        "message": str(message),
    }
    payload.update(extra)
    try:
        with open(BOT_EVENTS_FILE, 'a', encoding='utf-8') as f:
            f.write(_json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass

def append_ban_log(payload: dict):
    record = {"time": now_utc7_string()}
    record.update(payload or {})
    try:
        with open(BAN_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(_json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

def load_steamdb_patch_state():
    if os.path.exists(STEAMDB_PATCH_FILE):
        try:
            with open(STEAMDB_PATCH_FILE, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"seen": [], "seeded": False}

def save_steamdb_patch_state(state):
    atomic_write_json(STEAMDB_PATCH_FILE, state)

def load_spam_trap_state():
    if os.path.exists(SPAM_TRAP_STATE_FILE):
        try:
            with open(SPAM_TRAP_STATE_FILE, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            if isinstance(data, dict):
                data.setdefault("ban_count", 0)
                return data
        except Exception:
            pass
    return {"ban_count": 0, "counter_message_id": 0}

def save_spam_trap_state(state):
    atomic_write_json(SPAM_TRAP_STATE_FILE, state)

class SteamDBPatchParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._in_row = False
        self._in_cell = False
        self._cell = None
        self._cells = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self._in_row = True
            self._cells = []
        elif self._in_row and tag in ('td', 'th'):
            self._in_cell = True
            self._cell = {"text": "", "links": []}
        elif self._in_cell and tag == 'a':
            href = attrs.get('href', '')
            if href:
                self._cell["links"].append(href)

    def handle_data(self, data):
        if self._in_cell and self._cell is not None:
            self._cell["text"] += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._in_cell and self._cell is not None:
            self._cell["text"] = ' '.join(unescape(self._cell["text"]).split())
            self._cells.append(self._cell)
            self._cell = None
            self._in_cell = False
        elif tag == 'tr' and self._in_row:
            self._add_row()
            self._in_row = False
            self._cells = []

    def _add_row(self):
        app_cell = None
        title_cell = None
        app_id = None
        patch_id = None

        for cell in self._cells:
            for href in cell["links"]:
                app_match = re.search(r'/app/(\d+)/', href)
                patch_match = re.search(r'/patchnotes/(\d+)', href)
                if app_match:
                    app_id = app_match.group(1)
                    app_cell = cell
                if patch_match:
                    patch_id = patch_match.group(1)
                    title_cell = cell

        if not app_id or not title_cell:
            return

        date_text = self._cells[0]["text"] if self._cells else ''
        title = title_cell["text"] or 'Patch notes'
        game = app_cell["text"] if app_cell else f"App {app_id}"
        item_id = patch_id or f"{app_id}:{date_text}:{title}"
        self.rows.append({
            "id": item_id,
            "app_id": app_id,
            "game": game,
            "title": title,
            "date": date_text,
            "url": f"https://steamdb.info/patchnotes/{patch_id}/" if patch_id else f"https://steamdb.info/app/{app_id}/patchnotes/",
            "app_url": f"https://steamdb.info/app/{app_id}/patchnotes/",
        })

def fetch_steamdb_patches():
    url = "https://steamdb.info/patchnotes/"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; DiscordPatchWatcher/1.0; +https://steamdb.info/patchnotes/)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=STEAM_HTTP_TIMEOUT) as resp:
        html = resp.read().decode('utf-8', errors='replace')

    parser = SteamDBPatchParser()
    parser.feed(html)
    patches = parser.rows
    if STEAMDB_APP_IDS:
        patches = [patch for patch in patches if patch["app_id"] in STEAMDB_APP_IDS]
    return patches[:STEAMDB_PATCH_LIMIT]

def fetch_steam_event_patches():
    if not STEAMDB_APP_IDS:
        raise RuntimeError("Chua cau hinh STEAMDB_APP_IDS de lay update tu Steam Events.")

    patches = []
    cutoff_ts = steam_watcher_cutoff_ts()
    count_per_app = max(1, min(STEAMDB_PATCH_LIMIT, 100))
    for app_id in sorted(STEAMDB_APP_IDS):
        url = (
            "https://store.steampowered.com/events/ajaxgetadjacentpartnerevents/"
            f"?appid={app_id}&count_before=0&count_after={count_per_app}"
            f"&event_type_filter={steam_event_type_filter()}"
        )
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 DiscordPatchWatcher/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=STEAM_HTTP_TIMEOUT) as resp:
            data = _json.loads(resp.read().decode('utf-8', errors='replace'))

        if data.get("success") != 1:
            continue
        for event in data.get("events", []):
            date_value = (
                event.get("rtime32_start_time")
                or (event.get("announcement_body") or {}).get("posttime")
                or event.get("rtime_created")
            )
            if isinstance(date_value, int) and date_value < cutoff_ts:
                continue
            patch = steam_event_to_patch(app_id, event)
            if patch:
                patches.append(patch)

    patches.sort(key=lambda patch: patch.get("_sort_ts", 0), reverse=True)
    return patches[:STEAMDB_PATCH_LIMIT]

def fetch_recent_steam_news_for_app(app_id):
    url = (
        "https://store.steampowered.com/events/ajaxgetadjacentpartnerevents/"
        f"?appid={app_id}&count_before=0&count_after={STEAM_RECENT_PATCH_CHECK_COUNT}"
        f"&event_type_filter={steam_event_type_filter()}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 DiscordPatchWatcher/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=STEAM_HTTP_TIMEOUT) as resp:
        data = _json.loads(resp.read().decode('utf-8', errors='replace'))

    events = data.get("events", []) if data.get("success") == 1 else []
    patches = [steam_event_to_patch(app_id, event) for event in events]
    patches = [patch for patch in patches if patch]
    if not patches:
        return str(app_id), None

    patches.sort(key=lambda patch: patch.get("_sort_ts", 0), reverse=True)
    return str(app_id), patches[0]

async def fetch_recent_steam_news_for_apps_async(app_ids, timeout=RECENT_CHECK_TIMEOUT):
    app_ids = list(dict.fromkeys(str(app_id) for app_id in app_ids))
    recent = {app_id: None for app_id in app_ids}
    if not app_ids:
        return recent, []

    tasks = {
        asyncio.create_task(asyncio.to_thread(fetch_recent_steam_news_for_app, app_id)): app_id
        for app_id in app_ids
    }
    done, pending = await asyncio.wait(tasks.keys(), timeout=timeout)

    timed_out = [tasks[task] for task in pending]
    for task in pending:
        task.cancel()

    for task in done:
        app_id = tasks[task]
        try:
            key, patch = task.result()
            recent[str(key)] = patch
        except Exception as e:
            print(f"Steam Events recent check failed for {app_id}: {e}")
            recent[app_id] = None

    return recent, timed_out

def fetch_steam_app_name(app_id):
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&filters=basic"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 DiscordPatchWatcher/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=STEAM_HTTP_TIMEOUT) as resp:
        data = _json.loads(resp.read().decode('utf-8', errors='replace'))

    app_data = data.get(str(app_id), {})
    if not app_data.get("success"):
        raise RuntimeError(f"Steam khong tra ve thong tin cho App ID {app_id}.")

    name = app_data.get("data", {}).get("name")
    if not name:
        raise RuntimeError(f"Khong tim thay ten game cho App ID {app_id}.")
    return ' '.join(str(name).split())

def merge_patch_updates(*patch_groups):
    merged = []
    seen_ids = set()
    for patches in patch_groups:
        for patch in patches:
            patch_id = patch.get("id")
            if not patch_id or patch_id in seen_ids:
                continue
            seen_ids.add(patch_id)
            merged.append(patch)
    merged.sort(key=lambda patch: patch.get("_sort_ts", 0), reverse=True)
    return merged[:STEAMDB_PATCH_LIMIT]

def patch_seen_keys(patch):
    keys = []
    for field in ("id", "url"):
        value = str(patch.get(field) or "").strip()
        if value:
            keys.append(value)
    return keys

def fetch_patch_updates():
    steam_events = fetch_steam_event_patches()
    return merge_patch_updates(steam_events), "Steam Events"

async def get_steamdb_patch_channel():
    if not STEAMDB_PATCH_CHANNEL_ID:
        return None
    channel = bot.get_channel(STEAMDB_PATCH_CHANNEL_ID)
    if channel:
        return channel
    for guild in bot.guilds:
        try:
            channel = await guild.fetch_channel(STEAMDB_PATCH_CHANNEL_ID)
            if channel:
                return channel
        except Exception:
            pass
    return None

async def announce_steamdb_patch(channel, patch, mention=False):
    source = patch.get("source", "Steam Events")
    embed = discord.Embed(
        title=patch["title"][:256],
        description=f"**Game:** [{patch['game']}]({patch['app_url']})\n**App ID:** `{patch['app_id']}`",
        color=0x66c0f4
    )
    patch_url = safe_http_url(patch.get("url"))
    if patch_url:
        embed.add_field(name="Link", value=patch_url[:1024], inline=False)
    if patch.get("date"):
        embed.add_field(name="Time", value=patch["date"], inline=True)
    if patch.get("event_type"):
        embed.add_field(name="Type", value=patch["event_type"], inline=True)
    if patch.get("build_id"):
        embed.add_field(name="Build", value=patch["build_id"], inline=True)
    embed.set_footer(text=f"Patch Watcher - {source}")
    content = ""
    allowed_mentions = discord.AllowedMentions.none()
    if mention and STEAMDB_PATCH_MENTION_USER_IDS:
        mentions = " ".join(f"<@{user_id}>" for user_id in STEAMDB_PATCH_MENTION_USER_IDS)
        content = f"{mentions} Có patch/update mới."
        allowed_mentions = discord.AllowedMentions(users=True)
    await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)

async def send_recent_patch_info(destination, patch):
    source = patch.get("source", "Steam News")
    description = f"**Game:** [{patch['game']}]({patch['app_url']})\n**App ID:** `{patch['app_id']}`"
    summary = patch.get("summary")
    if summary:
        description += f"\n\n{summary[:900]}"
    embed = discord.Embed(
        title=patch["title"][:256],
        description=description[:4096],
        color=0x66c0f4
    )
    patch_url = safe_http_url(patch.get("url"))
    if patch_url:
        embed.add_field(name="Link", value=patch_url[:1024], inline=False)
    if patch.get("date"):
        embed.add_field(name="Time", value=patch["date"], inline=True)
    if patch.get("event_type"):
        embed.add_field(name="Type", value=patch["event_type"], inline=True)
    if patch.get("build_id"):
        embed.add_field(name="Build", value=patch["build_id"], inline=True)
    embed.set_footer(text=f"Recent patch/update - {source}")
    await destination.send(embed=embed)

def resolve_steam_check_selection(selection):
    if not STEAM_APP_ENTRIES:
        return []

    query = ' '.join(selection).strip()
    if not query:
        return []

    selected = []
    parts = [part.strip() for token in selection for part in token.split(',') if part.strip()]
    for part in parts:
        if part.isdigit():
            index = int(part)
            if 1 <= index <= len(STEAM_APP_ENTRIES):
                selected.append(STEAM_APP_ENTRIES[index - 1]["id"])
            elif part in STEAMDB_APP_IDS:
                selected.append(part)
            continue

        lowered = part.lower()
        for entry in STEAM_APP_ENTRIES:
            if lowered in entry["name"].lower() or lowered in entry["label"].lower():
                selected.append(entry["id"])
                break

    if not selected:
        lowered_query = query.lower()
        for entry in STEAM_APP_ENTRIES:
            if lowered_query in entry["name"].lower() or lowered_query in entry["label"].lower():
                selected.append(entry["id"])

    return list(dict.fromkeys(selected))

def build_steam_check_table():
    if not STEAM_APP_ENTRIES:
        return "Chua cau hinh STEAMDB_APP_IDS trong .env."

    lines = ["Bang game co the check:", "```text"]
    for index, entry in enumerate(STEAM_APP_ENTRIES, start=1):
        lines.append(f"{index:>2}. {entry['id']}_{entry['name']}")
    lines.extend(["```", "Dung: /check <so thu tu | app id | ten game>"])
    return "\n".join(lines)

def build_game_help():
    return (
        "Lenh game:\n"
        "/game list - hien bang game\n"
        "/game add <app_id> - them game, bot tu lay ten tu Steam\n"
        "/game remove <so thu tu | app_id | ten game> - xoa game\n"
        "/check <so thu tu | app_id | ten game> - xem patch/update gan nhat"
    )

def split_discord_text(text, limit=1900):
    text = str(text or '')
    if len(text) <= limit:
        return [text]

    chunks = []
    current = []
    current_len = 0
    in_code_block = False
    for line in text.splitlines():
        line_len = len(line) + 1
        if current and current_len + line_len > limit:
            chunk = "\n".join(current)
            if in_code_block:
                chunk += "\n```"
            chunks.append(chunk)
            current = ["```text"] if in_code_block else []
            current_len = len(current[0]) + 1 if current else 0

        current.append(line)
        current_len += line_len
        if line.startswith("```"):
            in_code_block = not in_code_block

    if current:
        chunk = "\n".join(current)
        if in_code_block:
            chunk += "\n```"
        chunks.append(chunk)
    return chunks

async def send_text_chunks(destination, text, **kwargs):
    for chunk in split_discord_text(text):
        await destination.send(chunk, **kwargs)
        await asyncio.sleep(0.2)

def reload_steam_app_config():
    global STEAMDB_APP_IDS_RAW, STEAM_APP_ENTRIES, STEAMDB_APP_IDS, STEAM_APP_NAMES
    STEAMDB_APP_IDS_RAW = os.getenv('STEAMDB_APP_IDS', '')
    STEAM_APP_ENTRIES = parse_steam_app_entries(STEAMDB_APP_IDS_RAW)
    STEAMDB_APP_IDS = {entry["id"] for entry in STEAM_APP_ENTRIES}
    STEAM_APP_NAMES = {entry["id"]: entry["name"] for entry in STEAM_APP_ENTRIES}

def save_steam_app_entries(entries):
    value = ', '.join(f"{entry['id']}_{entry['name']}" for entry in entries)
    dotenv.set_key(ENV_FILE, 'STEAMDB_APP_IDS', value)
    os.environ['STEAMDB_APP_IDS'] = value
    reload_steam_app_config()
    return value

def resolve_steam_app_entry_index(selection):
    if not STEAM_APP_ENTRIES:
        return None

    query = selection.strip()
    if not query:
        return None

    if query.isdigit():
        index = int(query)
        if 1 <= index <= len(STEAM_APP_ENTRIES):
            return index - 1
        for i, entry in enumerate(STEAM_APP_ENTRIES):
            if entry["id"] == query:
                return i

    lowered = query.lower()
    for i, entry in enumerate(STEAM_APP_ENTRIES):
        if lowered in entry["name"].lower() or lowered in entry["label"].lower():
            return i
    return None

async def steam_game_autocomplete(interaction: discord.Interaction, current: str):
    current_lower = (current or '').lower()
    choices = []
    for index, entry in enumerate(STEAM_APP_ENTRIES, start=1):
        label = f"{index}. {entry['id']}_{entry['name']}"
        if not current_lower or current_lower in label.lower():
            choices.append(app_commands.Choice(name=label[:100], value=str(index)))
        if len(choices) >= 25:
            break
    return choices

async def run_steamdb_patch_check(manual=False):
    if not STEAMDB_PATCH_CHANNEL_ID:
        log_event("steamdb_check", "Steam Events watcher chua cau hinh kenh thong bao.", "warn")
        return "Steam Events watcher chua duoc cau hinh kenh thong bao."

    channel = await get_steamdb_patch_channel()
    if not channel:
        log_event("steamdb_check", f"Khong tim thay kenh Steam Events ID {STEAMDB_PATCH_CHANNEL_ID}.", "warn")
        return f"Khong tim thay kenh Steam Events ID {STEAMDB_PATCH_CHANNEL_ID}."

    try:
        patches, source = await asyncio.to_thread(fetch_patch_updates)
    except (urllib.error.URLError, TimeoutError) as e:
        log_event("steamdb_check", f"Loi ket noi Steam Events: {e}", "error")
        return f"Loi ket noi Steam Events: {e}"
    except Exception as e:
        log_event("steamdb_check", f"Loi doc Steam Events: {e}", "error")
        return f"Loi doc Steam Events: {e}"

    if not patches:
        return "Khong tim thay patch/news phu hop voi cau hinh hien tai."

    state = load_steamdb_patch_state()
    seen = list(dict.fromkeys(str(item) for item in state.get("seen", [])))
    seen_set = set(seen)
    current_seen_keys = []
    for patch in patches:
        current_seen_keys.extend(patch_seen_keys(patch))
    current_seen_keys = list(dict.fromkeys(current_seen_keys))

    if not state.get("seeded") and not manual:
        state["seen"] = list(dict.fromkeys(current_seen_keys + seen))[:500]
        state["seeded"] = True
        save_steamdb_patch_state(state)
        return f"Da ghi nho {len(patches)} patch/news hien tai tu {source}, nhung muc moi sau do se duoc bao."

    new_patches = [
        patch for patch in patches
        if not any(key in seen_set for key in patch_seen_keys(patch))
    ]
    manual_latest = manual and bool(patches)
    if manual_latest and any(key in seen_set for key in patch_seen_keys(patches[0])):
        state["seen"] = list(dict.fromkeys(current_seen_keys + seen))[:500]
        state["seeded"] = True
        save_steamdb_patch_state(state)
        return f"Patch/update gan nhat tu {source} da duoc gui roi."

    patches_to_send = (patches[:1] if manual_latest else new_patches[:STEAM_WATCHER_SEND_LIMIT])
    failed_announcements = 0
    for patch in patches_to_send:
        try:
            await announce_steamdb_patch(channel, patch, mention=not manual)
        except discord.HTTPException as e:
            failed_announcements += 1
            log_event("steamdb_check", f"Khong gui duoc embed patch {patch.get('id')}: {e}", "error")
        await asyncio.sleep(0.2 if manual else 1)

    state["seen"] = list(dict.fromkeys(current_seen_keys + seen))[:500]
    state["seeded"] = True
    save_steamdb_patch_state(state)

    if manual_latest:
        sent_count = len(patches_to_send) - failed_announcements
        log_event("steamdb_check", f"Da gui patch/update gan nhat tu {source}.")
        if failed_announcements:
            return f"Khong gui duoc patch/update gan nhat tu {source}; loi {failed_announcements} muc."
        return f"Da gui patch/update gan nhat tu {source}."
    if new_patches:
        sent_count = len(patches_to_send) - failed_announcements
        skipped_count = max(0, len(new_patches) - len(patches_to_send))
        log_event("steamdb_check", f"Da gui {sent_count}/{len(new_patches)} patch/news moi tu {source}.")
        if failed_announcements:
            return f"Da gui {sent_count}/{len(new_patches)} patch/news moi tu {source}; loi {failed_announcements} muc."
        if skipped_count:
            return f"Da gui {sent_count}/{len(new_patches)} patch/news moi tu {source}; bo qua {skipped_count} muc de tranh spam."
        return f"Da gui {sent_count} patch/news moi tu {source}."
    log_event("steamdb_check", f"Chua co patch/news moi tu {source}.")
    return f"Chua co patch/news moi tu {source}."

def seconds_until_next_steamdb_check(now=None):
    now = now or datetime.datetime.now()
    if STEAMDB_PATCH_INTERVAL_HOURS:
        return STEAMDB_PATCH_INTERVAL_HOURS * 3600

    for hour in STEAMDB_PATCH_SCHEDULE_HOURS:
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target > now:
            return max(1, (target - now).total_seconds())
    target = (now + datetime.timedelta(days=1)).replace(
        hour=STEAMDB_PATCH_SCHEDULE_HOURS[0],
        minute=0,
        second=0,
        microsecond=0
    )
    return max(1, (target - now).total_seconds())

@tasks.loop(seconds=60)
async def check_steamdb_patches():
    wait_seconds = seconds_until_next_steamdb_check()
    print(f"SteamDB watcher: lan check tiep theo sau {int(wait_seconds)} giay.")
    await asyncio.sleep(wait_seconds)
    result = await run_steamdb_patch_check(manual=False)
    if result:
        print(f"SteamDB watcher: {result}")

async def export_channels_map():
    channels_map = {}
    for guild in bot.guilds:
        for ch in guild.text_channels:
            channels_map[str(ch.id)] = f"# {ch.name}"
        for ch in guild.voice_channels:
            channels_map[str(ch.id)] = f"Voice: {ch.name}"
        for thread in guild.threads:
            channels_map[str(thread.id)] = f"Thread: {thread.name}"
        for cat in guild.categories:
            channels_map[str(cat.id)] = f"Category: {cat.name}"
        for role in guild.roles:
            if role.name != "@everyone":
                channels_map[str(role.id)] = f"Role: {role.name}"
        for member in guild.members:
            channels_map[str(member.id)] = f"User: {member.display_name}"
    atomic_write_json(CHANNELS_FILE, channels_map)
    return len(channels_map)

@tasks.loop(seconds=2)
async def check_ipc_commands():
    try:
        import json
        if os.path.exists(IPC_CMD_FILE):
            with open(IPC_CMD_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Xóa file lệnh để tránh chạy lại trùng lặp
            os.remove(IPC_CMD_FILE)
            
            try:
                # Cố gắng đọc định dạng JSON mới cho IPC commands
                payload = json.loads(content)
                cmd = payload.get("command", "")
                args = payload.get("args", {})
            except json.JSONDecodeError:
                # Fallback: tương thích ngược với format chữ thuần
                cmd = content
                args = {}
                
            if cmd == "steamdb_check":
                print("Nhan lenh kiem tra SteamDB tu File Queue...")
                log_event("ipc", "Nhan lenh steamdb_check tu dashboard.")
                result = await run_steamdb_patch_check(manual=True)
                atomic_write_text(IPC_RESPONSE_FILE, result)

            elif cmd == "refresh_channels":
                print("Nhan lenh quet lai danh sach kenh tu File Queue...")
                total = await export_channels_map()
                log_event("ipc", f"Dashboard refresh_channels: da quet {total} muc.")
                atomic_write_text(IPC_RESPONSE_FILE, f"Da quet lai {total} muc kenh/role/user/thread.")

    except Exception as e:
        print(f"Lỗi đọc IPC: {e}")

@bot.command(name='ping', aliases=['online', 'status'])
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Bot vẫn đang online và hoạt động tốt!**\nĐộ trễ (Ping): `{latency}ms`")

# Sự kiện khi bot đã kết nối thành công và sẵn sàng
@bot.command(name='steamdbcheck', aliases=['patchcheck'])
@commands.has_permissions(manage_messages=True)
async def steamdb_check_command(ctx):
    await ctx.send("Dang lay patch/update gan nhat tu Steam Events...")
    result = await run_steamdb_patch_check(manual=True)
    await ctx.send(result)

@bot.command(name='check', aliases=['sdbcheckrecent', 'steamdbrecent', 'patchrecent'])
@commands.has_permissions(manage_messages=True)
async def steamdb_recent_command(ctx, *selection):
    if not selection:
        await send_text_chunks(ctx, build_steam_check_table())
        return

    app_ids = resolve_steam_check_selection(selection)
    if not app_ids:
        await send_text_chunks(ctx, "Khong tim thay game phu hop.\n" + build_steam_check_table())
        return

    await ctx.send(f"Dang lay patch/update gan nhat cho {len(app_ids)} game...")
    try:
        recent, timed_out = await fetch_recent_steam_news_for_apps_async(app_ids)
    except (urllib.error.URLError, TimeoutError, asyncio.TimeoutError) as e:
        await ctx.send(f"Loi ket noi Steam Events: {e}")
        return
    except Exception as e:
        await ctx.send(f"Loi doc Steam Events: {e}")
        return

    for app_id in app_ids:
        if app_id in timed_out:
            await ctx.send(f"Steam Events timeout cho Steam App ID `{app_id}`.")
            continue
        patch = recent.get(str(app_id))
        if patch:
            await send_recent_patch_info(ctx, patch)
        else:
            await ctx.send(f"Khong tim thay patch/update gan nhat cho Steam App ID `{app_id}`.")
        await asyncio.sleep(1)

@bot.command(name='dlt')
@commands.has_permissions(manage_messages=True)
async def delete_target_keyword_command(ctx, limit: int = 100):
    limit = max(1, min(int(limit or 100), 500))
    await ctx.send(f"Dang quet cac kenh trong TARGET_CATEGORY_IDS, {limit} tin gan nhat moi kenh...")
    result = await delete_target_keyword_messages_in_categories(ctx.guild, limit)
    await ctx.send(result)

@bot.group(name='game', invoke_without_command=True)
@commands.has_permissions(manage_messages=True)
async def steam_game_group(ctx):
    await send_text_chunks(ctx, build_game_help())

@steam_game_group.command(name='list', aliases=['ls'])
@commands.has_permissions(manage_messages=True)
async def steam_game_list_command(ctx):
    await send_text_chunks(ctx, build_steam_check_table())

@steam_game_group.command(name='add')
@commands.has_permissions(manage_messages=True)
async def steam_game_add_command(ctx, app_id: str):
    app_id = app_id.strip()
    if not app_id.isdigit():
        await ctx.send("App ID phai la so. Vi du: `game add 730`")
        return

    await ctx.send(f"Dang lay ten game cho App ID `{app_id}`...")
    try:
        game_name = await asyncio.to_thread(fetch_steam_app_name, app_id)
    except (urllib.error.URLError, TimeoutError) as e:
        await ctx.send(f"Loi ket noi Steam Store API: {e}")
        return
    except Exception as e:
        await ctx.send(f"Khong them duoc game: {e}")
        return

    entries = list(STEAM_APP_ENTRIES)
    for entry in entries:
        if entry["id"] == app_id:
            entry["name"] = game_name
            entry["label"] = f"{app_id}_{game_name}"
            save_steam_app_entries(entries)
            await send_text_chunks(ctx, f"Da cap nhat `{app_id}_{game_name}`.\n" + build_steam_check_table())
            return

    entries.append({"id": app_id, "name": game_name, "label": f"{app_id}_{game_name}"})
    save_steam_app_entries(entries)
    await send_text_chunks(ctx, f"Da them `{app_id}_{game_name}`.\n" + build_steam_check_table())

@steam_game_group.command(name='remove', aliases=['rm', 'delete', 'del'])
@commands.has_permissions(manage_messages=True)
async def steam_game_remove_command(ctx, *, selection: str):
    index = resolve_steam_app_entry_index(selection)
    if index is None:
        await send_text_chunks(ctx, "Khong tim thay game can xoa.\n" + build_steam_check_table())
        return

    entries = list(STEAM_APP_ENTRIES)
    removed = entries.pop(index)
    save_steam_app_entries(entries)
    await send_text_chunks(ctx, f"Da xoa `{removed['id']}_{removed['name']}`.\n" + build_steam_check_table())

@steam_game_group.command(name='help')
@commands.has_permissions(manage_messages=True)
async def steam_game_help_command(ctx):
    await send_text_chunks(ctx, build_game_help())

@bot.tree.command(name='ping', description='Kiem tra bot co online khong')
async def slash_ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Bot online. Ping: `{latency}ms`")

@bot.tree.command(name='steamdbcheck', description='Lay patch/update gan nhat theo cau hinh Steam watcher')
@app_commands.default_permissions(manage_messages=True)
async def slash_steamdbcheck(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send("Dang lay patch/update gan nhat tu Steam Events...")
    result = await run_steamdb_patch_check(manual=True)
    await interaction.followup.send(result)

@bot.tree.command(name='refreshchannels', description='Quet lai danh sach kenh/role/user/thread cho dashboard')
@app_commands.default_permissions(manage_messages=True)
async def slash_refreshchannels(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    total = await export_channels_map()
    await interaction.followup.send(f"Da quet lai {total} muc kenh/role/user/thread cho dashboard.")

@bot.tree.command(name='dlt', description='Quet TARGET_CATEGORY_IDS va xoa tin cua TARGET_USER_ID neu khop keyword')
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(limit='So tin gan nhat can quet moi kenh trong danh muc ap dung, toi da 500')
async def slash_delete_target_keyword_messages(interaction: discord.Interaction, limit: int = 100):
    await interaction.response.defer(thinking=True, ephemeral=True)
    result = await delete_target_keyword_messages_in_categories(interaction.guild, limit)
    await interaction.followup.send(result, ephemeral=True)

@bot.tree.command(name='check', description='Xem patch/update gan nhat cua game')
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(game='Chon so thu tu, App ID, hoac ten game')
@app_commands.autocomplete(game=steam_game_autocomplete)
async def slash_check(interaction: discord.Interaction, game: str | None = None):
    await interaction.response.defer(thinking=True)
    if not game:
        log_event("check", "Hien bang game cho /check.")
        await send_text_chunks(interaction.followup, build_steam_check_table())
        return

    app_ids = resolve_steam_check_selection([game])
    if not app_ids:
        log_event("check", f"Khong tim thay game phu hop: {game}", "warn")
        await send_text_chunks(interaction.followup, "Khong tim thay game phu hop.\n" + build_steam_check_table())
        return

    check_ids = app_ids
    print(f"/check slash: fetching recent Steam Events updates for {check_ids}")
    log_event("check", f"Dang lay patch/update cho {', '.join(check_ids)}.")
    await interaction.followup.send(f"Dang lay patch/update gan nhat cho {len(check_ids)} game...")
    try:
        recent, timed_out = await fetch_recent_steam_news_for_apps_async(check_ids)
    except (urllib.error.URLError, TimeoutError, asyncio.TimeoutError) as e:
        await interaction.followup.send(f"Loi ket noi Steam Events: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Loi doc Steam Events: {e}")
        return

    print(f"/check slash: finished recent Steam Events updates for {check_ids}")
    log_event("check", f"Da lay xong patch/update cho {', '.join(check_ids)}.")
    for app_id in check_ids:
        if app_id in timed_out:
            await interaction.followup.send(f"Steam Events timeout cho Steam App ID `{app_id}`.")
            continue
        patch = recent.get(str(app_id))
        if patch:
            await send_recent_patch_info(interaction.followup, patch)
        else:
            await interaction.followup.send(f"Khong tim thay patch/update gan nhat cho Steam App ID `{app_id}`.")
        await asyncio.sleep(1)

slash_game_group = app_commands.Group(
    name='game',
    description='Quan ly danh sach game Steam watcher'
)

@slash_game_group.command(name='list', description='Hien bang game dang cau hinh')
@app_commands.default_permissions(manage_messages=True)
async def slash_game_list(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await send_text_chunks(interaction.followup, build_steam_check_table())

@slash_game_group.command(name='add', description='Them game bang Steam App ID, bot tu lay ten game')
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(app_id='Steam App ID')
async def slash_game_add(interaction: discord.Interaction, app_id: str):
    app_id = app_id.strip()
    if not app_id.isdigit():
        await interaction.response.send_message("App ID phai la so. Vi du: /game add 730", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    try:
        game_name = await asyncio.to_thread(fetch_steam_app_name, app_id)
    except (urllib.error.URLError, TimeoutError) as e:
        await interaction.followup.send(f"Loi ket noi Steam Store API: {e}")
        return
    except Exception as e:
        await interaction.followup.send(f"Khong them duoc game: {e}")
        return

    entries = list(STEAM_APP_ENTRIES)
    for entry in entries:
        if entry["id"] == app_id:
            entry["name"] = game_name
            entry["label"] = f"{app_id}_{game_name}"
            save_steam_app_entries(entries)
            await send_text_chunks(interaction.followup, f"Da cap nhat `{app_id}_{game_name}`.\n" + build_steam_check_table())
            return

    entries.append({"id": app_id, "name": game_name, "label": f"{app_id}_{game_name}"})
    save_steam_app_entries(entries)
    await send_text_chunks(interaction.followup, f"Da them `{app_id}_{game_name}`.\n" + build_steam_check_table())

@slash_game_group.command(name='remove', description='Xoa game theo so thu tu, App ID hoac ten game')
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(game='Chon game can xoa')
@app_commands.autocomplete(game=steam_game_autocomplete)
async def slash_game_remove(interaction: discord.Interaction, game: str):
    index = resolve_steam_app_entry_index(game)
    if index is None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        await send_text_chunks(interaction.followup, "Khong tim thay game can xoa.\n" + build_steam_check_table(), ephemeral=True)
        return

    entries = list(STEAM_APP_ENTRIES)
    removed = entries.pop(index)
    save_steam_app_entries(entries)
    await interaction.response.defer(thinking=True)
    await send_text_chunks(interaction.followup, f"Da xoa `{removed['id']}_{removed['name']}`.\n" + build_steam_check_table())

@slash_game_group.command(name='help', description='Huong dan lenh game')
@app_commands.default_permissions(manage_messages=True)
async def slash_game_help(interaction: discord.Interaction):
    await interaction.response.send_message(build_game_help(), ephemeral=True)

bot.tree.add_command(slash_game_group)

@bot.command(name='refreshchannels', aliases=['rescanchannels'])
@commands.has_permissions(manage_messages=True)
async def refresh_channels_command(ctx):
    total = await export_channels_map()
    await ctx.send(f"Da quet lai {total} muc kenh/role/user/thread cho dashboard.")

@bot.event
async def on_ready():
    global slash_commands_synced
    if not check_ipc_commands.is_running():
        check_ipc_commands.start()
    if STEAMDB_PATCH_CHANNEL_ID and not check_steamdb_patches.is_running():
        check_steamdb_patches.start()
    if not slash_commands_synced:
        try:
            for guild in bot.guilds:
                bot.tree.clear_commands(guild=guild)
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync(guild=None)
            slash_commands_synced = True
            print(f"Da sync slash commands dang guild-only cho {len(bot.guilds)} guild va clear global commands.")
        except Exception as e:
            print(f"Loi sync slash commands: {e}")
    log_event("startup", f"Bot {bot.user} da ket noi.")
    print(f'Bot {bot.user} đã kết nối thành công!')
    
    # Xuất danh sách kênh + roles ra file để Web hiển thị tên
    try:
        channels_map = {}
        for guild in bot.guilds:
            for ch in guild.text_channels:
                channels_map[str(ch.id)] = f"# {ch.name}"
            for ch in guild.voice_channels:
                channels_map[str(ch.id)] = f"🔊 {ch.name}"
            for thread in guild.threads:
                channels_map[str(thread.id)] = f"💬 {thread.name}"
            for cat in guild.categories:
                channels_map[str(cat.id)] = f"📂 {cat.name}"
            for role in guild.roles:
                if role.name != "@everyone":
                    channels_map[str(role.id)] = f"🛡️ {role.name}"
            # Thêm cả User ID của bot target
            for member in guild.members:
                channels_map[str(member.id)] = f"👤 {member.display_name}"
        atomic_write_json(CHANNELS_FILE, channels_map)
        log_event("channels", f"Da xuat {len(channels_map)} muc ra channels.json.")
        print(f"Đã xuất {len(channels_map)} mục ra channels.json")
    except Exception as e:
        print(f"Lỗi xuất channels.json: {e}")
    
    if SUSPECT_CHANNEL_ID:
        for guild in bot.guilds:
            try:
                await sync_spam_trap_ban_counter(guild, increment=False)
            except Exception as e:
                print(f"Loi cap nhat bo dem ban spam trap: {e}")

    if STARTUP_CHANNEL_ID:
        channel = bot.get_channel(STARTUP_CHANNEL_ID)
        if channel:
            try:
                await channel.send("🟢 **Hệ thống phòng chống Spam đã được khởi động và đang sẵn sàng trực chiến!**")
            except discord.Forbidden:
                print(f"Cảnh báo: Bot không có quyền gửi tin nhắn vào kênh khởi động {STARTUP_CHANNEL_ID}")
        else:
            print(f"Cảnh báo: Không tìm thấy kênh thông báo online với ID {STARTUP_CHANNEL_ID}")

# Sự kiện khi một thành viên bị Ban khỏi server
@bot.event
async def on_member_ban(guild, user):
    if BAN_LOG_THREAD_ID:
        try:
            # Thử lấy kênh/thread từ cache
            log_channel = bot.get_channel(BAN_LOG_THREAD_ID)
            
            # Nếu không thấy trong cache, có thể là do khởi động lại, fetch thử từ guild
            if not log_channel:
                try:
                    log_channel = await guild.fetch_channel(BAN_LOG_THREAD_ID)
                except:
                    # fetch_channel cũng bao gồm cả thread (vì thread là subclass subclassing Discord Channels)
                    pass
            
            if log_channel:
                embed = discord.Embed(
                    title="Búa Tạ Đã Vung 🔨",
                    description=f"**Người dùng:** {user.name}#{user.discriminator}\n"
                                f"**ID:** `{user.id}`\n"
                                f"**Nhắc đến:** {user.mention}",
                    color=0xff0000
                )
                embed.set_footer(text="Hệ thống Ghi Log Ban Cố Định")
                
                # Fetch entry từ Audit Log để xem ai ban và lý do (tuỳ chọn)
                try:
                    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                        if entry.target.id == user.id:
                            embed.add_field(name="Ban bởi Admin", value=f"{entry.user.mention} (`{entry.user.id}`)", inline=False)
                            if entry.reason:
                                embed.add_field(name="Lý do", value=entry.reason, inline=False)
                            break
                except:
                    pass
                
                await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Lỗi khi gửi log ban: {e}")

# Sự kiện khi có một người dùng gửi tin nhắn trên server
@bot.event
async def on_message(message):
    # Bỏ qua tin nhắn nếu người gửi chính là con bot này
    if message.author == bot.user:
        return

    # Bỏ qua nếu tin nhắn thuộc Diễn đàn (ForumChannel)
    actual_channel = getattr(message.channel, 'parent', message.channel)
    if isinstance(actual_channel, discord.ForumChannel):
        return

    actual_channel_id = message.channel.parent.id if isinstance(message.channel, discord.Thread) else message.channel.id
    if await handle_spam_trap_message(message, actual_channel_id):
        return

    # Nếu ID của người gửi (hoặc bot khác) trùng với ID được chỉ định trong .env
    if message.author.id == TARGET_USER_ID:
        
        # Kiểm tra xem embed có chứa cụm từ vi phạm hay không bằng hàm helper
        if not has_violating_words(message):
            return

        # Lấy các thuộc tính thực sự của Kênh cho dù nó là Mẹ hay Thread
        is_thread = isinstance(message.channel, discord.Thread)
        actual_channel = message.channel.parent if is_thread else message.channel
        
        # Kiểm tra xem kênh hiện tại có nằm trong danh mục áp dụng không (chỉ dùng nếu có cấu hình danh mục)
        if TARGET_CATEGORY_IDS:
            if getattr(actual_channel, 'category_id', None) not in TARGET_CATEGORY_IDS:
                return # Bỏ qua nếu kênh không thuộc các danh mục chỉ định

        # Kiểm tra xem kênh hiện tại có nằm trong danh sách loại trừ không
        if EXCLUDED_CHANNEL_IDS:
            if actual_channel.id in EXCLUDED_CHANNEL_IDS:
                return # Bỏ qua nếu là kênh bị loại trừ

        try:
            # Xóa tin nhắn đó
            await message.delete()
            print(f"Đã xóa một tin nhắn nhúng (embed) của: {message.author.name} (ID: {TARGET_USER_ID}) tại kênh {message.channel.name}")
            log_event("auto_delete", f"Da xoa tin cua {message.author.id} tai #{getattr(message.channel, 'name', message.channel.id)}.")
        except discord.Forbidden:
            print("Lỗi: Bot của bạn chưa có quyền 'Manage Messages' (Quản lý tin nhắn) ở kênh này.")
        except discord.HTTPException as e:
            print(f"Lỗi không xác định khi xóa tin nhắn: {e}")

    # Process lệnh (nếu có)
    await bot.process_commands(message)


# Chạy bot bằng token lấy từ file .env
try:
    if __name__ == '__main__':
        if not TOKEN or TOKEN == 'điền_token_bot_của_bạn_vào_đây':
            print("Lỗi: Bạn chưa điền DISCORD_TOKEN trong file .env!")
        elif TARGET_USER_ID == 0:
            print("Cảnh báo: Bạn chưa cấu hình TARGET_USER_ID để xóa tin nhắn. Hãy điền vào file .env!")
            bot.run(TOKEN)
        else:
            print("Đang khởi động bot...")
            bot.run(TOKEN)
except KeyboardInterrupt:
    pass
except Exception as e:
    import traceback
    with open('bot_crash.log', 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
