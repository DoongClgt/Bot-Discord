"""steam.py - Steam/SteamDB patch watcher, lenh game/check, vong lap thong bao."""
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
import json as _json

from core import (
    bot, intents, TOKEN, parse_int_set, GENERAL_LOG_CHANNEL_ID, BAN_LOG_THREAD_ID, DELETE_LOG_THREAD_ID, DATA_DIR, STEAMDB_PATCH_FILE, CHANNELS_FILE, IPC_CMD_FILE, IPC_RESPONSE_FILE, BOT_EVENTS_FILE, BAN_LOG_FILE, SPAM_TRAP_STATE_FILE, TICKETS_STATE_FILE, TICKETS_COUNTER_FILE, TRANSCRIPT_DIR, TRANSCRIPT_INDEX_FILE, atomic_write_text, atomic_write_json, UTC7, now_utc7_string, log_event, append_ban_log, send_general_log, send_configured_ban_log,
)


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
STEAMDB_PATCH_INTERVAL_MINUTES_RAW = os.getenv('STEAMDB_PATCH_INTERVAL_MINUTES', '').strip()
STEAMDB_PATCH_INTERVAL_MINUTES = (
    int(STEAMDB_PATCH_INTERVAL_MINUTES_RAW)
    if STEAMDB_PATCH_INTERVAL_MINUTES_RAW.isdigit()
    else 0
)
STEAMDB_PATCH_INTERVAL_MINUTES = min(max(STEAMDB_PATCH_INTERVAL_MINUTES, 0), 1440)
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
    28: "NEWS / ANNOUNCEMENT",
}
STEAM_PATCH_EVENT_TYPES = {12, 13, 14}
STEAM_NEWS_PATCH_KEYWORDS = (
    "patch",
    "patch notes",
    "update",
    "hotfix",
    "changelog",
    "version",
)

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
    return "12,13,14,28"

def is_steam_patch_event(event, title, summary):
    event_type = event.get("event_type")
    if event_type in STEAM_PATCH_EVENT_TYPES:
        return True
    if event_type != 28:
        return False

    announcement = event.get("announcement_body") if isinstance(event.get("announcement_body"), dict) else {}
    text = " ".join(
        str(value or "")
        for value in (
            title,
            announcement.get("headline"),
        )
    ).lower()
    return any(keyword in text for keyword in STEAM_NEWS_PATCH_KEYWORDS)

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

    if not is_steam_patch_event(event, title, summary):
        return None

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
    interval_seconds = 0
    if STEAMDB_PATCH_INTERVAL_MINUTES:
        interval_seconds = STEAMDB_PATCH_INTERVAL_MINUTES * 60
    elif STEAMDB_PATCH_INTERVAL_HOURS:
        interval_seconds = STEAMDB_PATCH_INTERVAL_HOURS * 3600
    if interval_seconds:
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
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

@bot.tree.command(name='steamdbcheck', description='Lay patch/update gan nhat theo cau hinh Steam watcher')
@app_commands.default_permissions(manage_messages=True)
async def slash_steamdbcheck(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await interaction.followup.send("Dang lay patch/update gan nhat tu Steam Events...")
    result = await run_steamdb_patch_check(manual=True)
    await interaction.followup.send(result)

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
