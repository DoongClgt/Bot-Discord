"""bot.py - Entry point: admin/IPC, on_ready, khoi dong bot. Import cac module tinh nang."""
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
import moderation
import steam
import tickets
# import downloader  # Lenh /tiktok qua bot Discord da tat. Bat lai: bo comment dong nay (dashboard van tai duoc qua tiktok_api).
from moderation import sync_spam_trap_ban_counter, SPAM_TRAP_CHANNEL_IDS, TARGET_USER_ID
from steam import run_steamdb_patch_check, check_steamdb_patches, STEAMDB_PATCH_CHANNEL_ID
from tickets import TicketPanelView, TicketActionsView


STARTUP_CHANNEL_ID_STR = os.getenv('STARTUP_CHANNEL_ID', '')
STARTUP_CHANNEL_ID = int(STARTUP_CHANNEL_ID_STR) if STARTUP_CHANNEL_ID_STR.isdigit() else 0
slash_commands_synced = False

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

            elif cmd == "recount_ban_counter":
                print("Nhan lenh tinh lai bo dem ban tu File Queue...")
                total = await moderation.recount_and_sync_ban_counter()
                log_event("ipc", f"Dashboard recount_ban_counter: ban_count = {total}.")
                atomic_write_text(IPC_RESPONSE_FILE, f"Da cap nhat 'So mit to bit da ban' = {total}.")

    except Exception as e:
        print(f"Lỗi đọc IPC: {e}")

@bot.command(name='ping', aliases=['online', 'status'])
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Bot vẫn đang online và hoạt động tốt!**\nĐộ trễ (Ping): `{latency}ms`")

@bot.tree.command(name='ping', description='Kiem tra bot co online khong')
async def slash_ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Bot online. Ping: `{latency}ms`")

@bot.tree.command(name='refreshchannels', description='Quet lai danh sach kenh/role/user/thread cho dashboard')
@app_commands.default_permissions(manage_messages=True)
async def slash_refreshchannels(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    total = await export_channels_map()
    await interaction.followup.send(f"Da quet lai {total} muc kenh/role/user/thread cho dashboard.")

@bot.command(name='refreshchannels', aliases=['rescanchannels'])
@commands.has_permissions(manage_messages=True)
async def refresh_channels_command(ctx):
    total = await export_channels_map()
    await ctx.send(f"Da quet lai {total} muc kenh/role/user/thread cho dashboard.")
persistent_views_added = False


@bot.event
async def on_ready():
    global slash_commands_synced, persistent_views_added
    if not persistent_views_added:
        try:
            bot.add_view(TicketPanelView())
            bot.add_view(TicketActionsView())
            persistent_views_added = True
        except Exception as e:
            print(f"Loi register persistent views: {e}")
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
