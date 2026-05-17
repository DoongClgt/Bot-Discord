import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import os
import random
import re
import time
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

SPAM_TRAP_CHANNEL_ID_STR = os.getenv('SPAM_TRAP_CHANNEL_ID', '')
SPAM_TRAP_CHANNEL_ID = int(SPAM_TRAP_CHANNEL_ID_STR) if SPAM_TRAP_CHANNEL_ID_STR.isdigit() else 0
SPAM_TRAP_CHANNEL_ID_2_STR = os.getenv('SPAM_TRAP_CHANNEL_ID_2', '')
SPAM_TRAP_CHANNEL_ID_2 = int(SPAM_TRAP_CHANNEL_ID_2_STR) if SPAM_TRAP_CHANNEL_ID_2_STR.isdigit() else 0
SPAM_TRAP_CHANNEL_IDS = {channel_id for channel_id in (SPAM_TRAP_CHANNEL_ID, SPAM_TRAP_CHANNEL_ID_2) if channel_id}
SPAM_TRAP_EXCLUDED_ROLE_IDS = parse_int_set(os.getenv('SPAM_TRAP_EXCLUDED_ROLE_IDS', ''))

BAN_LOG_THREAD_ID_STR = os.getenv('BAN_LOG_THREAD_ID', '')
BAN_LOG_THREAD_ID = int(BAN_LOG_THREAD_ID_STR) if BAN_LOG_THREAD_ID_STR.isdigit() else 0

DELETE_LOG_THREAD_ID_STR = os.getenv('DELETE_LOG_THREAD_ID', '')
DELETE_LOG_THREAD_ID = int(DELETE_LOG_THREAD_ID_STR) if DELETE_LOG_THREAD_ID_STR.isdigit() else 0

STARTUP_CHANNEL_ID_STR = os.getenv('STARTUP_CHANNEL_ID', '')
STARTUP_CHANNEL_ID = int(STARTUP_CHANNEL_ID_STR) if STARTUP_CHANNEL_ID_STR.isdigit() else 0

NEW_MEMBER_ROLE_ID_STR = os.getenv('NEW_MEMBER_ROLE_ID', '')
NEW_MEMBER_ROLE_ID = int(NEW_MEMBER_ROLE_ID_STR) if NEW_MEMBER_ROLE_ID_STR.isdigit() else 0
AUTO_ROLE_ON_JOIN_ENABLED = os.getenv('AUTO_ROLE_ON_JOIN_ENABLED', 'true').strip().lower() not in ('false', '0', 'no', 'off', '')

TICKET_CATEGORY_ID_STR = os.getenv('TICKET_CATEGORY_ID', '')
TICKET_CATEGORY_ID = int(TICKET_CATEGORY_ID_STR) if TICKET_CATEGORY_ID_STR.isdigit() else 0
TICKET_CONFIRMED_CATEGORY_ID_STR = os.getenv('TICKET_CONFIRMED_CATEGORY_ID', '')
TICKET_CONFIRMED_CATEGORY_ID = int(TICKET_CONFIRMED_CATEGORY_ID_STR) if TICKET_CONFIRMED_CATEGORY_ID_STR.isdigit() else 0
TICKET_CLOSED_CATEGORY_ID_STR = os.getenv('TICKET_CLOSED_CATEGORY_ID', '')
TICKET_CLOSED_CATEGORY_ID = int(TICKET_CLOSED_CATEGORY_ID_STR) if TICKET_CLOSED_CATEGORY_ID_STR.isdigit() else 0
TICKET_SUPPORT_ROLE_IDS = parse_int_set(os.getenv('TICKET_SUPPORT_ROLE_IDS', os.getenv('TICKET_SUPPORT_ROLE_ID', '')))
TICKET_LOG_CHANNEL_ID_STR = os.getenv('TICKET_LOG_CHANNEL_ID', '')
TICKET_LOG_CHANNEL_ID = int(TICKET_LOG_CHANNEL_ID_STR) if TICKET_LOG_CHANNEL_ID_STR.isdigit() else 0

TICKET_PANEL_TITLE_DEFAULT = '🎫 Hệ thống ticket'
TICKET_PANEL_DESCRIPTION_DEFAULT = (
    'Bấm nút bên dưới để mở một ticket riêng với đội ngũ. '
    'Một channel mới sẽ được tạo cho riêng bạn.\n\n'
    '• Mỗi user chỉ mở được 1 ticket cùng lúc.\n'
    '• Đội ngũ sẽ phản hồi sớm nhất có thể.'
)
TICKET_PANEL_TITLE = os.getenv('TICKET_PANEL_TITLE', '').strip() or TICKET_PANEL_TITLE_DEFAULT
TICKET_PANEL_DESCRIPTION = os.getenv('TICKET_PANEL_DESCRIPTION', '').strip() or TICKET_PANEL_DESCRIPTION_DEFAULT

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
intents.members = True


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

async def sync_spam_trap_ban_counter(guild: discord.Guild, increment: bool = False):
    state = load_spam_trap_state()
    current_count = int(state.get("ban_count", 0) or 0)
    if increment:
        state["ban_count"] = current_count + 1
    message_text = f"Số mít tơ bít đã ban: {state['ban_count']}"
    counter_messages = state.setdefault("counter_messages", {})

    for channel_id in SPAM_TRAP_CHANNEL_IDS:
        channel = guild.get_channel(channel_id) or bot.get_channel(channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(channel_id)
            except Exception:
                channel = None
        if not channel:
            continue

        key = str(channel_id)
        message_id = int(counter_messages.get(key) or 0)
        if message_id:
            try:
                counter_message = await channel.fetch_message(message_id)
                await counter_message.edit(content=message_text)
                continue
            except Exception:
                counter_messages[key] = 0

        try:
            counter_message = await channel.send(message_text)
            counter_messages[key] = counter_message.id
        except discord.Forbidden:
            pass

    save_spam_trap_state(state)

async def update_spam_trap_ban_counter(guild: discord.Guild):
    await sync_spam_trap_ban_counter(guild, increment=True)

# In-memory chống xử lý ban trùng cho cùng (guild, user) khi gateway gửi MESSAGE_CREATE 2 lần
_spam_trap_banning: set = set()

async def ban_spam_trap_suspect(message: discord.Message, reason_text: str, audit_reason: str):
    guild = message.guild
    if guild is None:
        return

    ban_key = (guild.id, message.author.id)
    if ban_key in _spam_trap_banning:
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        return
    _spam_trap_banning.add(ban_key)

    try:
        await message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

    author = message.author
    channel = message.channel
    roles_snapshot = []
    if isinstance(author, discord.Member):
        roles_snapshot = [
            {"id": str(r.id), "name": r.name}
            for r in author.roles
            if r.id != guild.id
        ]
    parent_channel = channel.parent if isinstance(channel, discord.Thread) else None

    try:
        await guild.ban(
            author,
            reason=audit_reason,
            delete_message_seconds=60,
        )
        await update_spam_trap_ban_counter(guild)
        log_event("spam_trap_ban", f"Da ban {author.id}: {reason_text}")
        append_ban_log({
            "guild_id": str(guild.id),
            "guild_name": guild.name,
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
        _spam_trap_banning.discard(ban_key)
        await send_configured_ban_log(guild, f"Khong ban duoc {author.mention}: bot thieu quyen Ban Members hoac role thap.")
    except discord.HTTPException as e:
        _spam_trap_banning.discard(ban_key)
        await send_configured_ban_log(guild, f"Khong ban duoc {author.mention}: {e}")

def has_spam_trap_excluded_role(member: discord.Member):
    if not SPAM_TRAP_EXCLUDED_ROLE_IDS:
        return False
    return any(role.id in SPAM_TRAP_EXCLUDED_ROLE_IDS for role in member.roles)

async def handle_spam_trap_message(message: discord.Message, actual_channel_id: int):
    if not isinstance(message.author, discord.Member) or not message.guild:
        return False

    if actual_channel_id not in SPAM_TRAP_CHANNEL_IDS:
        return False

    if has_spam_trap_excluded_role(message.author):
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        log_event("spam_trap", f"Xoa tin nhan tu {message.author.id}: co role mien tru, khong ban.")
        return True

    await ban_spam_trap_suspect(
        message,
        "Da chat vao kenh bay.",
        "Spam trap: chat vao kenh bay",
    )
    return True

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
TICKETS_STATE_FILE = os.path.join(DATA_DIR, 'tickets.json')
TICKETS_COUNTER_FILE = os.path.join(DATA_DIR, 'tickets_counter.txt')
TRANSCRIPT_DIR = os.path.join(DATA_DIR, 'transcripts')
TRANSCRIPT_INDEX_FILE = os.path.join(DATA_DIR, 'transcripts_index.jsonl')
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
GIVEAWAYS_STATE_FILE = os.path.join(DATA_DIR, 'giveaways.json')
GIVEAWAYS_HISTORY_FILE = os.path.join(DATA_DIR, 'giveaways_history.jsonl')

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
                data.setdefault("counter_messages", {})
                data.pop("counter_message_id", None)
                return data
        except Exception:
            pass
    return {"ban_count": 0, "counter_messages": {}}

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
    app_ids = sorted(STEAMDB_APP_IDS)
    failed_apps = 0
    last_error = None
    for app_id in app_ids:
        url = (
            "https://store.steampowered.com/events/ajaxgetadjacentpartnerevents/"
            f"?appid={app_id}&count_before=0&count_after={count_per_app}"
            f"&event_type_filter={steam_event_type_filter()}"
        )
        data = None
        for attempt in range(2):
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 DiscordPatchWatcher/1.0",
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=STEAM_HTTP_TIMEOUT) as resp:
                    data = _json.loads(resp.read().decode('utf-8', errors='replace'))
                break
            except (urllib.error.URLError, TimeoutError) as e:
                last_error = e
                if attempt == 0:
                    time.sleep(2)
                    continue
                failed_apps += 1
                log_event(
                    "steamdb_check",
                    f"Bo qua app {app_id} sau 2 lan thu: {e}",
                    "warn",
                )
                data = None

        if data is None:
            continue
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

    if failed_apps and failed_apps == len(app_ids) and last_error is not None:
        raise last_error

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
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        interval_seconds = STEAMDB_PATCH_INTERVAL_HOURS * 3600
        seconds_since_midnight = (now - midnight).total_seconds()
        next_offset = (int(seconds_since_midnight) // interval_seconds + 1) * interval_seconds
        target = midnight + datetime.timedelta(seconds=next_offset)
        return max(1, (target - now).total_seconds())

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

            elif cmd == "giveaway_start":
                prize = str(args.get("prize", "")).strip()
                duration_str = str(args.get("duration", "")).strip()
                winners = max(1, min(50, int(args.get("winners", 1) or 1)))
                desc = str(args.get("description", "") or "").strip()
                rrid = str(args.get("required_role_id", "") or "").strip()
                cid = str(args.get("channel_id", "") or "").strip()
                ping_target = str(args.get("ping_target", "") or "").strip() or None
                seconds = parse_duration(duration_str)
                if not prize or seconds <= 0 or not cid.isdigit():
                    atomic_write_text(IPC_RESPONSE_FILE, "Tham so khong hop le.")
                else:
                    target = bot.get_channel(int(cid))
                    if not isinstance(target, discord.TextChannel):
                        atomic_write_text(IPC_RESPONSE_FILE, "Channel khong hop le hoac khong tim thay.")
                    else:
                        host_id = bot.user.id if bot.user else 0
                        msg, err = await create_giveaway(
                            channel=target,
                            host_id=host_id,
                            host_name="Dashboard",
                            prize=prize,
                            duration_seconds=seconds,
                            winners=winners,
                            description=desc,
                            required_role_id=int(rrid) if rrid.isdigit() else None,
                            ping_target=ping_target,
                        )
                        if err:
                            atomic_write_text(IPC_RESPONSE_FILE, err)
                        else:
                            log_event("ipc", f"Dashboard giveaway_start: {msg.id} '{prize}'.")
                            atomic_write_text(IPC_RESPONSE_FILE, f"Da tao giveaway: {msg.jump_url}")

            elif cmd == "giveaway_end":
                mid = str(args.get("message_id", ""))
                if not mid.isdigit():
                    atomic_write_text(IPC_RESPONSE_FILE, "Message ID khong hop le.")
                else:
                    log_event("ipc", f"Dashboard giveaway_end {mid}.")
                    winners = await end_giveaway(mid, reason='dashboard')
                    if winners is None:
                        atomic_write_text(IPC_RESPONSE_FILE, "Khong tim thay giveaway hoac da end.")
                    else:
                        atomic_write_text(IPC_RESPONSE_FILE, f"Da end. {len(winners)} winner.")

            elif cmd == "giveaway_reroll":
                mid = str(args.get("message_id", ""))
                cnt = int(args.get("count", 1) or 1)
                if not mid.isdigit():
                    atomic_write_text(IPC_RESPONSE_FILE, "Message ID khong hop le.")
                else:
                    log_event("ipc", f"Dashboard giveaway_reroll {mid} count={cnt}.")
                    winners, err = await reroll_giveaway(mid, cnt)
                    if err:
                        atomic_write_text(IPC_RESPONSE_FILE, err)
                    else:
                        atomic_write_text(IPC_RESPONSE_FILE, f"Da chon lai. {len(winners)} nguoi thang moi.")

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

# ===== Ticket system =====

_ticket_create_lock = asyncio.Lock()
persistent_views_added = False

def load_tickets_state() -> dict:
    if not os.path.exists(TICKETS_STATE_FILE):
        return {}
    try:
        with open(TICKETS_STATE_FILE, 'r', encoding='utf-8') as f:
            return _json.load(f)
    except (OSError, _json.JSONDecodeError):
        return {}

def save_tickets_state(state: dict):
    atomic_write_json(TICKETS_STATE_FILE, state)

def next_ticket_number() -> int:
    n = 0
    if os.path.exists(TICKETS_COUNTER_FILE):
        try:
            with open(TICKETS_COUNTER_FILE, 'r', encoding='utf-8') as f:
                n = int(f.read().strip() or '0')
        except (OSError, ValueError):
            n = 0
    n += 1
    atomic_write_text(TICKETS_COUNTER_FILE, str(n))
    return n

def find_ticket_by_user(user_id: int):
    state = load_tickets_state()
    for cid, info in state.items():
        if info.get('user_id') == user_id:
            return cid, info
    return None

def append_transcript_index(record: dict):
    try:
        with open(TRANSCRIPT_INDEX_FILE, 'a', encoding='utf-8') as f:
            f.write(_json.dumps(record, ensure_ascii=False) + '\n')
    except OSError:
        pass

async def build_transcript_text(channel: discord.TextChannel, info: dict) -> str:
    lines = []
    lines.append(f"Ticket #{info.get('ticket_number'):04d} — {channel.name}")
    lines.append(f"User: {info.get('user_name')} ({info.get('user_id')})")
    lines.append(f"Opened: {info.get('opened_at')}")
    if info.get('confirmed_by'):
        lines.append(
            f"Confirmed by: {info.get('confirmed_by_name')} ({info.get('confirmed_by')}) at {info.get('confirmed_at')}"
        )
    if info.get('closed_by'):
        lines.append(
            f"Closed (archived) by: {info.get('closed_by_name')} ({info.get('closed_by')}) at {info.get('closed_at')}"
        )
    lines.append(
        f"Deleted: {info.get('deleted_at')} by {info.get('deleted_by_name')} ({info.get('deleted_by')})"
    )
    lines.append("=" * 60)
    lines.append("")
    try:
        async for m in channel.history(limit=None, oldest_first=True):
            ts = m.created_at.astimezone(UTC7).strftime("%d-%m-%Y %H:%M:%S")
            author = f"{m.author.display_name} ({m.author.id})"
            content = m.content or ""
            lines.append(f"[{ts}] {author}: {content}")
            for emb in m.embeds:
                t = (emb.title or "").strip()
                d = (emb.description or "").strip()
                if t or d:
                    lines.append(f"    [embed] {t} — {d}")
            for att in m.attachments:
                lines.append(f"    [attachment] {att.filename} {att.url}")
    except discord.HTTPException as e:
        lines.append(f"(Loi doc lich su channel: {e})")
    return "\n".join(lines)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Tạo ticket', style=discord.ButtonStyle.primary, emoji='🎫', custom_id='ticket:open')
    async def open_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ticket_open(interaction)


class TicketActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Xác nhận', style=discord.ButtonStyle.success, emoji='✅', custom_id='ticket:claim')
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ticket_confirm(interaction)

    @discord.ui.button(label='Close', style=discord.ButtonStyle.secondary, emoji='🔒', custom_id='ticket:close')
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ticket_close(interaction)

    @discord.ui.button(label='Delete', style=discord.ButtonStyle.danger, emoji='🗑️', custom_id='ticket:delete')
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ticket_delete_request(interaction)


class TicketDeleteConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label='Xác nhận xóa', style=discord.ButtonStyle.danger, emoji='🗑️')
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_ticket_delete_confirm(interaction)

    @discord.ui.button(label='Hủy', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content='Đã hủy.', view=None)


async def handle_ticket_open(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message('Chỉ dùng trong server.', ephemeral=True)
        return
    if not TICKET_CATEGORY_ID:
        await interaction.response.send_message('Chưa cấu hình TICKET_CATEGORY_ID trong .env.', ephemeral=True)
        return

    guild = interaction.guild
    user = interaction.user

    existing = find_ticket_by_user(user.id)
    if existing:
        cid, _info = existing
        ch = guild.get_channel(int(cid))
        if ch is not None:
            await interaction.response.send_message(
                f'Bạn đã có ticket đang mở: {ch.mention}', ephemeral=True,
            )
            return
        # stale entry — clean and continue
        state = load_tickets_state()
        state.pop(cid, None)
        save_tickets_state(state)

    await interaction.response.defer(ephemeral=True, thinking=True)

    async with _ticket_create_lock:
        existing = find_ticket_by_user(user.id)
        if existing:
            cid, _info = existing
            ch = guild.get_channel(int(cid))
            if ch is not None:
                await interaction.followup.send(
                    f'Bạn đã có ticket đang mở: {ch.mention}', ephemeral=True,
                )
                return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send(
                'TICKET_CATEGORY_ID không phải category hợp lệ.', ephemeral=True,
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True,
                manage_messages=True, read_message_history=True, attach_files=True, embed_links=True,
            ),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True,
            ),
        }
        for rid in TICKET_SUPPORT_ROLE_IDS:
            support = guild.get_role(rid)
            if support:
                overwrites[support] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    read_message_history=True, attach_files=True, embed_links=True,
                )

        number = next_ticket_number()
        safe_name = re.sub(r'[^a-z0-9-]+', '-', user.name.lower()).strip('-') or 'user'
        ch_name = f"{number:04d}-{safe_name}"[:100]
        try:
            channel = await guild.create_text_channel(
                name=ch_name, category=category, overwrites=overwrites,
                reason=f'Ticket cho {user.id}',
                topic=f'Ticket #{number:04d} | user_id={user.id}',
            )
        except discord.Forbidden:
            await interaction.followup.send('Bot không có quyền tạo channel trong category này.', ephemeral=True)
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f'Tạo channel lỗi: {e}', ephemeral=True)
            return

        opened_at = now_utc7_string()
        info = {
            'channel_id': str(channel.id),
            'channel_name': channel.name,
            'guild_id': str(guild.id),
            'ticket_number': number,
            'user_id': user.id,
            'user_name': str(user),
            'opened_at': opened_at,
            'confirmed_by': None,
            'confirmed_by_name': None,
            'confirmed_at': None,
        }
        state = load_tickets_state()
        state[str(channel.id)] = info
        save_tickets_state(state)

        embed = discord.Embed(
            title=f'🎫 Ticket #{number:04d}',
            description=(
                f'Xin chào {user.mention}, đội ngũ sẽ phản hồi sớm nhất có thể.\n'
                f'Vui lòng mô tả vấn đề của bạn ở đây.\n\n'
                f'**✅ Xác nhận** — staff xác nhận đã xử lý, chuyển ticket sang category đã xác nhận.\n'
                f'**🔒 Close** — staff đóng ticket, lưu lại trong category archived.\n'
                f'**🗑️ Delete** — staff xóa hẳn ticket, lưu transcript.'
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(name='Mở bởi', value=f'{user.mention}\n`{user.id}`', inline=True)
        embed.add_field(name='Thời gian', value=opened_at, inline=True)
        embed.set_footer(text=f'channel.id = {channel.id}')
        try:
            await channel.send(
                content=user.mention, embed=embed,
                view=TicketActionsView(),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
            )
        except discord.HTTPException:
            pass

        log_event('ticket_open', f'Ticket #{number:04d} mo cho {user.id} ({user}). channel={channel.id}')
        await interaction.followup.send(f'Đã tạo ticket: {channel.mention}', ephemeral=True)


def _user_is_support(member) -> bool:
    if not TICKET_SUPPORT_ROLE_IDS:
        return True
    if not isinstance(member, discord.Member):
        return False
    return any(member.get_role(rid) is not None for rid in TICKET_SUPPORT_ROLE_IDS)


async def handle_ticket_confirm(interaction: discord.Interaction):
    state = load_tickets_state()
    info = state.get(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message('Đây không phải ticket đang mở.', ephemeral=True)
        return
    if not _user_is_support(interaction.user):
        await interaction.response.send_message('Bạn không có quyền xác nhận ticket này.', ephemeral=True)
        return
    if info.get('confirmed_by'):
        await interaction.response.send_message(
            f"Ticket đã được xác nhận bởi <@{info['confirmed_by']}>.", ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=False)

    staff_part = re.sub(r'[^a-z0-9-]+', '-', interaction.user.name.lower()).strip('-') or 'staff'
    user_raw = (info.get('user_name') or '').split('#')[0]
    user_part = re.sub(r'[^a-z0-9-]+', '-', user_raw.lower()).strip('-') or 'user'
    new_name = f"{info['ticket_number']:04d}-{staff_part}-{user_part}"[:100]

    edit_kwargs = {'reason': f"Ticket #{info['ticket_number']:04d} xac nhan boi {interaction.user.id}"}
    if new_name and new_name != interaction.channel.name:
        edit_kwargs['name'] = new_name

    moved = False
    move_error = None
    if TICKET_CONFIRMED_CATEGORY_ID and interaction.guild is not None:
        new_cat = interaction.guild.get_channel(TICKET_CONFIRMED_CATEGORY_ID)
        if isinstance(new_cat, discord.CategoryChannel):
            edit_kwargs['category'] = new_cat
        else:
            move_error = 'TICKET_CONFIRMED_CATEGORY_ID không phải category hợp lệ.'

    renamed = False
    edit_error = None
    if 'name' in edit_kwargs or 'category' in edit_kwargs:
        try:
            await interaction.channel.edit(**edit_kwargs)
            renamed = 'name' in edit_kwargs
            moved = 'category' in edit_kwargs
        except discord.Forbidden:
            edit_error = 'Bot không có quyền edit channel (cần Manage Channels).'
        except discord.HTTPException as e:
            edit_error = f'Edit channel lỗi: {e}'

    info['confirmed_by'] = interaction.user.id
    info['confirmed_by_name'] = str(interaction.user)
    info['confirmed_at'] = now_utc7_string()
    if renamed:
        info['channel_name'] = new_name
    state[str(interaction.channel.id)] = info
    save_tickets_state(state)

    msg = f'✅ {interaction.user.mention} đã xác nhận ticket này.'
    if renamed:
        msg += f' Channel đổi tên thành `{new_name}`.'
    if moved:
        msg += f' Đã chuyển sang <#{TICKET_CONFIRMED_CATEGORY_ID}>.'
    if edit_error:
        msg += f'\n⚠️ {edit_error}'
    elif move_error:
        msg += f'\n⚠️ {move_error}'
    await interaction.followup.send(msg)
    log_event(
        'ticket_confirm',
        f"Ticket #{info['ticket_number']:04d} xac nhan boi {interaction.user.id}. moved={moved} renamed={renamed}",
    )


async def handle_ticket_close(interaction: discord.Interaction):
    state = load_tickets_state()
    info = state.get(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message('Đây không phải ticket đang mở.', ephemeral=True)
        return
    if not _user_is_support(interaction.user):
        await interaction.response.send_message('Bạn không có quyền đóng ticket này.', ephemeral=True)
        return

    await interaction.response.defer(thinking=False)

    moved = False
    move_error = None
    if TICKET_CLOSED_CATEGORY_ID and interaction.guild is not None:
        new_cat = interaction.guild.get_channel(TICKET_CLOSED_CATEGORY_ID)
        if isinstance(new_cat, discord.CategoryChannel):
            try:
                await interaction.channel.edit(
                    category=new_cat,
                    reason=f"Ticket #{info['ticket_number']:04d} dong boi {interaction.user.id}",
                )
                moved = True
            except discord.Forbidden:
                move_error = 'Bot không có quyền move channel sang category đã đóng.'
            except discord.HTTPException as e:
                move_error = f'Move channel lỗi: {e}'
        else:
            move_error = 'TICKET_CLOSED_CATEGORY_ID không phải category hợp lệ.'

    info['closed_by'] = interaction.user.id
    info['closed_by_name'] = str(interaction.user)
    info['closed_at'] = now_utc7_string()
    state[str(interaction.channel.id)] = info
    save_tickets_state(state)

    msg = f'🔒 {interaction.user.mention} đã đóng ticket này.'
    if moved:
        msg += f' Đã chuyển sang <#{TICKET_CLOSED_CATEGORY_ID}>.'
    elif move_error:
        msg += f'\n⚠️ {move_error}'
    await interaction.followup.send(msg)
    log_event('ticket_close', f"Ticket #{info['ticket_number']:04d} dong boi {interaction.user.id}. moved={moved}")


async def handle_ticket_delete_request(interaction: discord.Interaction):
    state = load_tickets_state()
    info = state.get(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message('Đây không phải ticket đang mở.', ephemeral=True)
        return
    if not _user_is_support(interaction.user):
        await interaction.response.send_message('Bạn không có quyền xóa ticket này.', ephemeral=True)
        return
    await interaction.response.send_message(
        '⚠️ Xác nhận **xóa hẳn** ticket? Transcript sẽ được lưu, channel sẽ bị xóa vĩnh viễn.',
        view=TicketDeleteConfirmView(), ephemeral=True,
    )


async def handle_ticket_delete_confirm(interaction: discord.Interaction):
    channel = interaction.channel
    state = load_tickets_state()
    info = state.get(str(channel.id))
    if not info:
        try:
            await interaction.response.edit_message(content='Ticket không tồn tại.', view=None)
        except discord.HTTPException:
            pass
        return

    try:
        await interaction.response.edit_message(
            content='Đang xóa ticket và lưu transcript...', view=None,
        )
    except discord.HTTPException:
        pass

    info['deleted_by'] = interaction.user.id
    info['deleted_by_name'] = str(interaction.user)
    info['deleted_at'] = now_utc7_string()

    try:
        transcript_text = await build_transcript_text(channel, info)
    except Exception as e:
        transcript_text = f'(Loi build transcript: {e})'

    filename = f"ticket-{info['ticket_number']:04d}-{channel.id}.txt"
    file_path = os.path.join(TRANSCRIPT_DIR, filename)
    saved = False
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(transcript_text)
        saved = True
    except OSError:
        pass

    record = {
        'ticket_number': info['ticket_number'],
        'channel_id': str(channel.id),
        'channel_name': info['channel_name'],
        'user_id': info['user_id'],
        'user_name': info['user_name'],
        'opened_at': info['opened_at'],
        'closed_at': info['deleted_at'],
        'closed_by': info['deleted_by'],
        'closed_by_name': info['deleted_by_name'],
        'confirmed_by': info.get('confirmed_by'),
        'confirmed_by_name': info.get('confirmed_by_name'),
        'archived_by': info.get('closed_by'),
        'archived_by_name': info.get('closed_by_name'),
        'archived_at': info.get('closed_at'),
        'filename': filename,
    }
    append_transcript_index(record)

    if TICKET_LOG_CHANNEL_ID and interaction.guild is not None:
        log_ch = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_ch is not None:
            embed = discord.Embed(
                title=f"🗑️ Ticket #{info['ticket_number']:04d} đã xóa",
                color=discord.Color.dark_grey(),
            )
            embed.add_field(name='User', value=f"<@{info['user_id']}>\n`{info['user_id']}`", inline=True)
            embed.add_field(name='Xóa bởi', value=f"<@{info['deleted_by']}>", inline=True)
            if info.get('confirmed_by'):
                embed.add_field(name='Xác nhận bởi', value=f"<@{info['confirmed_by']}>", inline=True)
            if info.get('closed_by'):
                embed.add_field(name='Đóng (archive) bởi', value=f"<@{info['closed_by']}>", inline=True)
            embed.add_field(name='Mở lúc', value=info['opened_at'], inline=False)
            embed.add_field(name='Xóa lúc', value=info['deleted_at'], inline=False)
            try:
                if saved:
                    await log_ch.send(embed=embed, file=discord.File(file_path, filename=filename))
                else:
                    await log_ch.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException, FileNotFoundError):
                pass

    state.pop(str(channel.id), None)
    save_tickets_state(state)
    log_event(
        'ticket_delete',
        f"Ticket #{info['ticket_number']:04d} xoa boi {interaction.user.id}. transcript={filename}",
    )

    await asyncio.sleep(3)
    try:
        await channel.delete(reason=f"Ticket #{info['ticket_number']:04d} deleted")
    except (discord.Forbidden, discord.HTTPException):
        pass


@bot.tree.command(name='ticket_panel', description='Dang panel mo ticket vao kenh hien tai')
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def slash_ticket_panel(interaction: discord.Interaction):
    if interaction.channel is None:
        await interaction.response.send_message('Khong tim thay kenh.', ephemeral=True)
        return
    embed = discord.Embed(
        title=TICKET_PANEL_TITLE,
        description=TICKET_PANEL_DESCRIPTION,
        color=discord.Color.blurple(),
    )
    try:
        await interaction.channel.send(embed=embed, view=TicketPanelView())
    except discord.Forbidden:
        await interaction.response.send_message('Bot khong gui duoc tin trong kenh nay.', ephemeral=True)
        return
    await interaction.response.send_message('Đã đăng panel ticket.', ephemeral=True)


@bot.event
async def on_guild_channel_delete(channel):
    state = load_tickets_state()
    key = str(getattr(channel, 'id', ''))
    if key and key in state:
        info = state.pop(key)
        save_tickets_state(state)
        log_event(
            'ticket_orphan',
            f"Channel ticket #{info.get('ticket_number'):04d} bi xoa thu cong, da clean state.",
        )

# ===== Giveaway system =====

_giveaway_lock = asyncio.Lock()
_DURATION_PATTERN = re.compile(r'^\s*(\d+)\s*([smhdw])\s*$', re.IGNORECASE)
_DURATION_UNITS = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
GIVEAWAY_MIN_SECONDS = 10
GIVEAWAY_MAX_SECONDS = 30 * 86400  # 30 ngay

def parse_duration(text: str) -> int:
    """Parse '10s', '5m', '1h', '2d', '1w' -> seconds. Return 0 if invalid."""
    if not text:
        return 0
    m = _DURATION_PATTERN.match(text)
    if not m:
        return 0
    n = int(m.group(1))
    unit = m.group(2).lower()
    return n * _DURATION_UNITS[unit]

def format_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "đã kết thúc"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if not parts and secs:
        parts.append(f"{secs}s")
    return " ".join(parts) or "<1m"

def load_giveaways() -> dict:
    if not os.path.exists(GIVEAWAYS_STATE_FILE):
        return {}
    try:
        with open(GIVEAWAYS_STATE_FILE, 'r', encoding='utf-8') as f:
            return _json.load(f)
    except (OSError, _json.JSONDecodeError):
        return {}

def save_giveaways(state: dict):
    atomic_write_json(GIVEAWAYS_STATE_FILE, state)

def append_giveaway_history(record: dict):
    try:
        with open(GIVEAWAYS_HISTORY_FILE, 'a', encoding='utf-8') as f:
            f.write(_json.dumps(record, ensure_ascii=False) + '\n')
    except OSError:
        pass

def build_giveaway_embed(gw: dict, *, ended: bool = False, cancelled: bool = False) -> discord.Embed:
    entrants_count = len(gw.get('entrants', []))
    ends_unix = int(gw.get('ends_at_unix', 0))
    prize = gw.get('prize', '?')
    description = (gw.get('description') or '').strip()

    if cancelled:
        title = "Đã hủy quay thưởng"
        color = discord.Color.from_rgb(96, 96, 96)
    elif ended:
        title = "Đã kết thúc quay thưởng"
        color = discord.Color.from_rgb(96, 96, 96)
    else:
        title = "Quay thưởng"
        color = discord.Color.from_rgb(255, 196, 60)

    parts = [f"## {prize}"]
    if description:
        parts.append("")
        parts.append(description)
    parts.append("")

    if cancelled:
        parts.append("**Đợt quay thưởng đã bị hủy.** Không có người trúng.")
    elif ended:
        winners = gw.get('winners', [])
        if winners:
            mentions = ', '.join(f'<@{w}>' for w in winners)
            parts.append(f"**Người thắng:** {mentions}")
        else:
            parts.append("**Người thắng:** *Không có ai tham gia*")
        parts.append(f"**Kết thúc lúc:** <t:{ends_unix}:F>")
        parts.append(f"**Tổng số người tham gia:** {entrants_count}")
    else:
        parts.append(f"**Kết thúc sau:** <t:{ends_unix}:R>  ·  <t:{ends_unix}:f>")
        parts.append(f"**Số người thắng:** {gw.get('winners_count', 1)}")
        if gw.get('required_role_id'):
            parts.append(f"**Yêu cầu vai trò:** <@&{gw['required_role_id']}>")
        parts.append(f"**Đã tham gia:** {entrants_count}")

    embed = discord.Embed(
        title=title,
        description="\n".join(parts),
        color=color,
    )

    if gw.get('host_id') and not cancelled:
        host_name = gw.get('host_name') or 'staff'
        embed.set_footer(text=f"Mở bởi {host_name}")

    return embed


class GiveawayEnterView(discord.ui.View):
    def __init__(self, *, count: int = 0, ended: bool = False, cancelled: bool = False):
        super().__init__(timeout=None)
        btn = self.children[0]
        if cancelled:
            btn.label = "Đã hủy"
            btn.style = discord.ButtonStyle.secondary
            btn.disabled = True
        elif ended:
            btn.label = f"Đã kết thúc · {count} người"
            btn.style = discord.ButtonStyle.secondary
            btn.disabled = True
        else:
            btn.label = f"Tham gia ({count})"
            btn.disabled = False

    @discord.ui.button(label='Tham gia', style=discord.ButtonStyle.primary, emoji='🎉', custom_id='giveaway:enter')
    async def enter_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_giveaway_enter(interaction)


async def handle_giveaway_enter(interaction: discord.Interaction):
    mid = str(interaction.message.id)
    async with _giveaway_lock:
        state = load_giveaways()
        gw = state.get(mid)
        if not gw:
            await interaction.response.send_message('Đợt quay thưởng này không còn trong hệ thống.', ephemeral=True)
            return
        if gw.get('cancelled'):
            await interaction.response.send_message('Đợt quay thưởng này đã bị hủy.', ephemeral=True)
            return
        if gw.get('ended'):
            await interaction.response.send_message('Đợt quay thưởng này đã kết thúc.', ephemeral=True)
            return
        if time.time() >= gw.get('ends_at_unix', 0):
            await interaction.response.send_message('Đợt quay thưởng đã hết hạn — đợi bot xử lý.', ephemeral=True)
            return

        required = gw.get('required_role_id')
        if required:
            member = interaction.user if isinstance(interaction.user, discord.Member) else None
            if member is None or member.get_role(int(required)) is None:
                await interaction.response.send_message(
                    f'Bạn cần role <@&{required}> để tham gia giveaway này.', ephemeral=True,
                )
                return

        entrants = gw.setdefault('entrants', [])
        uid = interaction.user.id
        if uid in entrants:
            entrants.remove(uid)
            removed = True
        else:
            entrants.append(uid)
            removed = False
        state[mid] = gw
        save_giveaways(state)

    try:
        await interaction.message.edit(
            embed=build_giveaway_embed(gw),
            view=GiveawayEnterView(count=len(entrants)),
        )
    except discord.HTTPException:
        pass

    if removed:
        await interaction.response.send_message('❌ Đã hủy tham gia.', ephemeral=True)
    else:
        await interaction.response.send_message('✅ Đã tham gia! Bấm lại nút để hủy.', ephemeral=True)


async def end_giveaway(message_id: str, *, reason: str = 'scheduled', winners_override: int = None):
    async with _giveaway_lock:
        state = load_giveaways()
        gw = state.get(message_id)
        if not gw or gw.get('ended') or gw.get('cancelled'):
            return None
        # Mark ended early to prevent re-entry
        gw['ended'] = True
        gw['ended_at_unix'] = int(time.time())
        save_giveaways(state)

    pool = list(dict.fromkeys(gw.get('entrants', [])))  # de-dup keep order
    n_winners = winners_override if winners_override is not None else gw.get('winners_count', 1)
    n_winners = max(1, n_winners)
    winners = random.sample(pool, min(n_winners, len(pool))) if pool else []
    gw['winners'] = winners

    async with _giveaway_lock:
        state = load_giveaways()
        state[message_id] = gw
        save_giveaways(state)

    channel = bot.get_channel(int(gw['channel_id']))
    if channel is not None:
        try:
            msg = await channel.fetch_message(int(message_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            msg = None
        if msg is not None:
            try:
                await msg.edit(
                    embed=build_giveaway_embed(gw, ended=True),
                    view=GiveawayEnterView(count=len(pool), ended=True),
                )
            except discord.HTTPException:
                pass
            if winners:
                mentions = ' '.join(f'<@{w}>' for w in winners)
                try:
                    await channel.send(
                        f"🎉 Chúc mừng {mentions}! Các bạn đã thắng **{gw['prize']}**.",
                        reference=msg,
                        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
                    )
                except discord.HTTPException:
                    pass
            else:
                try:
                    await channel.send(
                        f"😢 Đợt quay thưởng **{gw['prize']}** đã kết thúc nhưng không có ai tham gia.",
                        reference=msg,
                    )
                except discord.HTTPException:
                    pass

    append_giveaway_history({
        'message_id': message_id,
        'channel_id': gw.get('channel_id'),
        'guild_id': gw.get('guild_id'),
        'host_id': gw.get('host_id'),
        'prize': gw.get('prize'),
        'winners_count': gw.get('winners_count'),
        'entrants_count': len(pool),
        'winners': winners,
        'created_at_unix': gw.get('created_at_unix'),
        'ends_at_unix': gw.get('ends_at_unix'),
        'ended_at_unix': gw.get('ended_at_unix'),
        'reason': reason,
    })
    log_event(
        'giveaway_end',
        f"Giveaway {message_id} ended ({reason}), {len(winners)}/{len(pool)} winners.",
    )
    return winners


async def reroll_giveaway(message_id: str, count: int = 1):
    state = load_giveaways()
    gw = state.get(message_id)
    if not gw:
        return None, 'Không tìm thấy đợt quay thưởng trong hệ thống.'
    if not gw.get('ended'):
        return None, 'Đợt quay thưởng chưa kết thúc, không chọn lại được.'

    all_entrants = list(dict.fromkeys(gw.get('entrants', [])))
    previous_set = set(gw.get('previous_winners', [])) | set(gw.get('winners', []))
    pool = [u for u in all_entrants if u not in previous_set]

    if not all_entrants:
        return [], 'Không có ai tham gia.'
    if not pool:
        return [], 'Đã hết người để chọn — tất cả người tham gia đều đã thắng rồi.'

    count = max(1, count)
    pick = min(count, len(pool))
    warning = None
    if count > len(pool):
        warning = f'Chỉ còn {len(pool)} người chưa thắng, đã chọn hết.'

    new_winners = random.sample(pool, pick)
    gw['previous_winners'] = list(previous_set)
    gw['winners'] = new_winners
    gw['rerolled_at_unix'] = int(time.time())
    state[message_id] = gw
    save_giveaways(state)

    channel = bot.get_channel(int(gw['channel_id']))
    if channel is not None:
        try:
            msg = await channel.fetch_message(int(message_id))
            await msg.edit(
                embed=build_giveaway_embed(gw, ended=True),
                view=GiveawayEnterView(count=len(all_entrants), ended=True),
            )
            mentions = ' '.join(f'<@{w}>' for w in new_winners)
            text = f"🎲 Đã chọn lại người thắng cho **{gw['prize']}**: {mentions}!"
            if warning:
                text += f"\n⚠️ {warning}"
            await channel.send(
                text,
                reference=msg,
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
            )
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    log_event(
        'giveaway_reroll',
        f"Giveaway {message_id} reroll: {len(new_winners)} nguoi thang moi, loai {len(previous_set)} nguoi da tung thang.",
    )
    return new_winners, None


async def create_giveaway(
    *,
    channel: discord.TextChannel,
    host_id: int,
    host_name: str,
    prize: str,
    duration_seconds: int,
    winners: int,
    description: str = '',
    required_role_id: int = None,
    ping_target: str = None,
):
    """Core logic tao giveaway, dung chung cho slash + IPC. Tra ve (msg|None, error_str|None).

    ping_target: "everyone" | "here" | "<role_id>" | None.
    """
    if duration_seconds < GIVEAWAY_MIN_SECONDS:
        return None, f'Duration tối thiểu {GIVEAWAY_MIN_SECONDS}s.'
    if duration_seconds > GIVEAWAY_MAX_SECONDS:
        return None, 'Duration tối đa 30 ngày.'
    if winners < 1 or winners > 50:
        return None, 'Số người thắng phải từ 1 đến 50.'
    if not prize.strip():
        return None, 'Thiếu prize.'

    now = int(time.time())
    ends_at = now + duration_seconds
    gw = {
        'channel_id': str(channel.id),
        'guild_id': str(channel.guild.id),
        'host_id': host_id,
        'host_name': host_name,
        'prize': prize,
        'description': description or '',
        'winners_count': winners,
        'required_role_id': str(required_role_id) if required_role_id else None,
        'created_at_unix': now,
        'ends_at_unix': ends_at,
        'entrants': [],
        'ended': False,
        'cancelled': False,
        'winners': [],
    }

    ping_content = ""
    allowed = discord.AllowedMentions(everyone=False, roles=False, users=False)
    if ping_target == "everyone":
        ping_content = "@everyone"
        allowed = discord.AllowedMentions(everyone=True, roles=False, users=False)
    elif ping_target == "here":
        ping_content = "@here"
        allowed = discord.AllowedMentions(everyone=True, roles=False, users=False)
    elif ping_target and str(ping_target).isdigit():
        ping_content = f"<@&{ping_target}>"
        allowed = discord.AllowedMentions(everyone=False, roles=True, users=False)

    send_kwargs = {
        'embed': build_giveaway_embed(gw),
        'view': GiveawayEnterView(count=0),
        'allowed_mentions': allowed,
    }
    if ping_content:
        send_kwargs['content'] = ping_content
    try:
        msg = await channel.send(**send_kwargs)
    except discord.Forbidden:
        return None, f'Bot không gửi được tin trong {channel.mention}.'
    except discord.HTTPException as e:
        return None, f'Lỗi gửi tin nhắn: {e}'

    gw['message_id'] = str(msg.id)
    state = load_giveaways()
    state[str(msg.id)] = gw
    save_giveaways(state)

    log_event(
        'giveaway_start',
        f"Giveaway {msg.id} '{prize}' boi {host_id}, end in {duration_seconds}s, winners={winners}.",
    )
    return msg, None


async def cancel_giveaway(message_id: str, by_user_id: int):
    async with _giveaway_lock:
        state = load_giveaways()
        gw = state.get(message_id)
        if not gw or gw.get('ended') or gw.get('cancelled'):
            return False
        gw['cancelled'] = True
        gw['ended'] = True
        gw['ended_at_unix'] = int(time.time())
        gw['cancelled_by'] = by_user_id
        state[message_id] = gw
        save_giveaways(state)

    channel = bot.get_channel(int(gw['channel_id']))
    if channel is not None:
        try:
            msg = await channel.fetch_message(int(message_id))
            await msg.edit(
                embed=build_giveaway_embed(gw, cancelled=True),
                view=GiveawayEnterView(count=len(gw.get('entrants', [])), cancelled=True),
            )
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    log_event('giveaway_cancel', f"Giveaway {message_id} cancelled by {by_user_id}.")
    return True


giveaway_group = app_commands.Group(
    name='giveaway',
    description='Quản lý đợt quay thưởng',
    default_permissions=discord.Permissions(manage_guild=True),
)


@giveaway_group.command(name='start', description='Tạo đợt quay thưởng mới')
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    prize='Phần thưởng',
    duration='Ví dụ: 10m, 1h, 2d, 1w (tối thiểu 10s, tối đa 30 ngày)',
    winners='Số người thắng (mặc định 1)',
    description='Mô tả thêm (tùy chọn)',
    required_role='Vai trò bắt buộc để tham gia (tùy chọn)',
    channel='Kênh đăng (mặc định là kênh hiện tại)',
    ping_role='Vai trò sẽ ping khi đăng (tùy chọn)',
    ping_everyone='Ping @everyone khi đăng (tùy chọn)',
)
async def gw_start(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int = 1,
    description: str = '',
    required_role: discord.Role = None,
    channel: discord.TextChannel = None,
    ping_role: discord.Role = None,
    ping_everyone: bool = False,
):
    if interaction.guild is None:
        await interaction.response.send_message('Chi dung trong server.', ephemeral=True)
        return

    seconds = parse_duration(duration)
    if seconds <= 0:
        await interaction.response.send_message(
            'Duration không hợp lệ. Dùng format: `10s`, `5m`, `1h`, `2d`, `1w`.', ephemeral=True,
        )
        return

    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message('Channel target không hợp lệ.', ephemeral=True)
        return

    ping_target = None
    if ping_everyone:
        ping_target = "everyone"
    elif ping_role:
        ping_target = str(ping_role.id)

    msg, err = await create_giveaway(
        channel=target_channel,
        host_id=interaction.user.id,
        host_name=str(interaction.user),
        prize=prize,
        duration_seconds=seconds,
        winners=winners,
        description=description,
        required_role_id=required_role.id if required_role else None,
        ping_target=ping_target,
    )
    if err:
        await interaction.response.send_message(f'⚠️ {err}', ephemeral=True)
        return
    await interaction.response.send_message(
        f'✅ Đã tạo giveaway trong {target_channel.mention}: [link]({msg.jump_url})',
        ephemeral=True,
    )


@giveaway_group.command(name='end', description='Kết thúc sớm đợt quay thưởng')
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(message_id='ID tin nhắn của đợt quay thưởng')
async def gw_end(interaction: discord.Interaction, message_id: str):
    if not message_id.isdigit():
        await interaction.response.send_message('Message ID phải là số.', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    winners = await end_giveaway(message_id, reason=f'manual:{interaction.user.id}')
    if winners is None:
        await interaction.followup.send('Không tìm thấy giveaway hoặc đã kết thúc.', ephemeral=True)
        return
    if winners:
        mentions = ', '.join(f'<@{w}>' for w in winners)
        await interaction.followup.send(f'✅ Đã kết thúc. Người thắng: {mentions}', ephemeral=True)
    else:
        await interaction.followup.send('✅ Đã kết thúc. Không có ai tham gia.', ephemeral=True)


@giveaway_group.command(name='reroll', description='Chọn lại người thắng cho đợt đã kết thúc')
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(message_id='ID tin nhắn của đợt quay thưởng', count='Số người thắng cần chọn lại (mặc định 1)')
async def gw_reroll(interaction: discord.Interaction, message_id: str, count: int = 1):
    if not message_id.isdigit():
        await interaction.response.send_message('Message ID phải là số.', ephemeral=True)
        return
    if count < 1 or count > 50:
        await interaction.response.send_message('Số lượng phải từ 1 đến 50.', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    winners, err = await reroll_giveaway(message_id, count)
    if err:
        await interaction.followup.send(f'⚠️ {err}', ephemeral=True)
        return
    if winners:
        mentions = ', '.join(f'<@{w}>' for w in winners)
        await interaction.followup.send(f'🎲 Đã chọn lại. Người thắng mới: {mentions}', ephemeral=True)
    else:
        await interaction.followup.send('🎲 Đã chọn lại nhưng không có ai tham gia.', ephemeral=True)


@giveaway_group.command(name='cancel', description='Hủy đợt đang chạy (không chọn người thắng)')
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(message_id='ID tin nhắn của đợt quay thưởng')
async def gw_cancel(interaction: discord.Interaction, message_id: str):
    if not message_id.isdigit():
        await interaction.response.send_message('Message ID phải là số.', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    ok = await cancel_giveaway(message_id, interaction.user.id)
    if ok:
        await interaction.followup.send('🚫 Đã hủy đợt quay thưởng.', ephemeral=True)
    else:
        await interaction.followup.send('Không tìm thấy đợt quay thưởng hoặc đã kết thúc.', ephemeral=True)


@giveaway_group.command(name='list', description='Liệt kê các đợt quay thưởng đang chạy')
@app_commands.checks.has_permissions(manage_guild=True)
async def gw_list(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message('Chi dung trong server.', ephemeral=True)
        return
    state = load_giveaways()
    gid = str(interaction.guild.id)
    active = [
        gw for gw in state.values()
        if gw.get('guild_id') == gid and not gw.get('ended') and not gw.get('cancelled')
    ]
    if not active:
        await interaction.response.send_message('Không có đợt quay thưởng nào đang chạy.', ephemeral=True)
        return
    lines = []
    now = int(time.time())
    for gw in sorted(active, key=lambda g: g.get('ends_at_unix', 0)):
        remaining = format_remaining(gw.get('ends_at_unix', now) - now)
        lines.append(
            f"• **{gw.get('prize', '?')}** · <#{gw['channel_id']}> · còn {remaining} · "
            f"{len(gw.get('entrants', []))} người · [xem](https://discord.com/channels/{gid}/{gw['channel_id']}/{gw['message_id']})"
        )
    embed = discord.Embed(
        title=f'🎉 Đợt quay thưởng đang chạy ({len(active)})',
        description='\n'.join(lines),
        color=discord.Color.from_rgb(255, 196, 60),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.tree.add_command(giveaway_group)


@tasks.loop(seconds=30)
async def check_giveaways():
    try:
        state = load_giveaways()
        now = time.time()
        for mid in list(state.keys()):
            gw = state[mid]
            if gw.get('ended') or gw.get('cancelled'):
                continue
            if now >= gw.get('ends_at_unix', 0):
                try:
                    await end_giveaway(mid, reason='scheduled')
                except Exception as e:
                    log_event('giveaway_end_error', f"{mid}: {e}", level='error')
    except Exception as e:
        log_event('giveaway_loop_error', str(e), level='error')


@check_giveaways.before_loop
async def _wait_ready_giveaway():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    global slash_commands_synced, persistent_views_added
    if not persistent_views_added:
        try:
            bot.add_view(TicketPanelView())
            bot.add_view(TicketActionsView())
            bot.add_view(GiveawayEnterView())
            persistent_views_added = True
        except Exception as e:
            print(f"Loi register persistent views: {e}")
    if not check_ipc_commands.is_running():
        check_ipc_commands.start()
    if not check_giveaways.is_running():
        check_giveaways.start()
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
    
    if SPAM_TRAP_CHANNEL_IDS:
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

# Sự kiện khi có thành viên mới tham gia server — tự động cấp role mặc định
@bot.event
async def on_member_join(member: discord.Member):
    if not AUTO_ROLE_ON_JOIN_ENABLED:
        return
    if not NEW_MEMBER_ROLE_ID:
        return
    if member.bot:
        return
    if any(role.id == NEW_MEMBER_ROLE_ID for role in member.roles):
        return
    role = member.guild.get_role(NEW_MEMBER_ROLE_ID)
    if role is None:
        log_event("auto_role", f"Khong tim thay role ID {NEW_MEMBER_ROLE_ID} trong guild {member.guild.id}.", "warn")
        return
    try:
        await member.add_roles(role, reason="Auto role cho thanh vien moi")
        log_event("auto_role", f"Da cap role {role.name} cho {member.id} ({member.display_name}).")
    except discord.Forbidden:
        log_event("auto_role", f"Bot khong co quyen cap role {role.name} cho {member.id}.", "error")
    except discord.HTTPException as e:
        log_event("auto_role", f"Loi khi cap role {role.name} cho {member.id}: {e}", "error")

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
