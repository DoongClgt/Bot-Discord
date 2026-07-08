"""core.py - Nen tang dung chung: bot, config chung, helper, log, IPC file paths."""
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


# Tải cấu hình từ file .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

def parse_int_set(raw_value):
    return {
        int(item.strip())
        for item in str(raw_value or '').split(',')
        if item.strip().isdigit()
    }

BAN_LOG_THREAD_ID_STR = os.getenv('BAN_LOG_THREAD_ID', '')
BAN_LOG_THREAD_ID = int(BAN_LOG_THREAD_ID_STR) if BAN_LOG_THREAD_ID_STR.isdigit() else 0

DELETE_LOG_THREAD_ID_STR = os.getenv('DELETE_LOG_THREAD_ID', '')
DELETE_LOG_THREAD_ID = int(DELETE_LOG_THREAD_ID_STR) if DELETE_LOG_THREAD_ID_STR.isdigit() else 0

GENERAL_LOG_CHANNEL_ID_STR = os.getenv('GENERAL_LOG_CHANNEL_ID', '')
GENERAL_LOG_CHANNEL_ID = int(GENERAL_LOG_CHANNEL_ID_STR) if GENERAL_LOG_CHANNEL_ID_STR.isdigit() else 0

# Khởi tạo intents để bot có quyền đọc được tin nhắn trên server
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# Khai báo bot
bot = commands.Bot(command_prefix='/', intents=intents)

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
