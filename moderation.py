"""moderation.py - Spam trap, xoa tin keyword, auto role, member/message events."""
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


# Lấy từ khóa cấm từ .env
TARGET_KEYWORDS_RAW = os.getenv('TARGET_KEYWORDS', 'bad word usage, too many infractions')
TARGET_KEYWORDS = [kw.strip().lower() for kw in TARGET_KEYWORDS_RAW.split(',') if kw.strip()]

# ID của người hoặc bot mà bạn muốn xóa tin nhắn (lấy từ tùy chọn .env)
TARGET_USER_ID = int(os.getenv('TARGET_USER_ID', 0))

# Lấy danh sách ID danh mục (category) cần xóa tin nhắn (cách nhau bởi dấu phẩy)
category_ids_str = os.getenv('TARGET_CATEGORY_IDS', '')
TARGET_CATEGORY_IDS = [int(cat_id.strip()) for cat_id in category_ids_str.split(',')] if category_ids_str else []

# Lấy danh sách ID kênh (channel) muốn loại trừ, không xóa tin nhắn ở đây
excluded_channel_ids_str = os.getenv('EXCLUDED_CHANNEL_IDS', '')
EXCLUDED_CHANNEL_IDS = [int(ch_id.strip()) for ch_id in excluded_channel_ids_str.split(',')] if excluded_channel_ids_str else []

# Kênh bẫy spam: SPAM_TRAP_CHANNEL_IDS là danh sách ID cách nhau bằng dấu phẩy (số kênh tuỳ ý).
# SPAM_TRAP_CHANNEL_ID / SPAM_TRAP_CHANNEL_ID_2 là biến cũ, vẫn đọc để .env cũ không mất cấu hình.
SPAM_TRAP_CHANNEL_IDS = parse_int_set(os.getenv('SPAM_TRAP_CHANNEL_IDS', ''))
SPAM_TRAP_CHANNEL_IDS |= parse_int_set(os.getenv('SPAM_TRAP_CHANNEL_ID', ''))
SPAM_TRAP_CHANNEL_IDS |= parse_int_set(os.getenv('SPAM_TRAP_CHANNEL_ID_2', ''))
SPAM_TRAP_CHANNEL_IDS.discard(0)
SPAM_TRAP_EXCLUDED_ROLE_IDS = parse_int_set(os.getenv('SPAM_TRAP_EXCLUDED_ROLE_IDS', ''))

# Số giây tin nhắn của người bị spam-trap ban sẽ bị Discord xóa (mọi kênh).
# Mặc định 1 tiếng (3600) để xóa cả tin cũ ở các kênh ngoài; tối đa Discord cho phép là 604800.
def _parse_delete_seconds(raw_value, default):
    try:
        seconds = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return default
    return max(0, min(seconds, 604800))

SPAM_TRAP_BAN_DELETE_SECONDS = _parse_delete_seconds(
    os.getenv('SPAM_TRAP_BAN_DELETE_SECONDS', ''), 3600
)

NEW_MEMBER_ROLE_ID_STR = os.getenv('NEW_MEMBER_ROLE_ID', '')
NEW_MEMBER_ROLE_ID = int(NEW_MEMBER_ROLE_ID_STR) if NEW_MEMBER_ROLE_ID_STR.isdigit() else 0
AUTO_ROLE_ON_JOIN_ENABLED = os.getenv('AUTO_ROLE_ON_JOIN_ENABLED', 'true').strip().lower() not in ('false', '0', 'no', 'off', '')

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

def count_ban_log_entries():
    """Đếm số ban spam trap (unique) trong ban_log.jsonl, bỏ qua dòng trùng (chỉ khác 'time').

    Ban do admin tự tay thực hiện (source='admin') KHÔNG được tính: bộ đếm trong kênh bẫy
    là 'số mít tơ bít đã ban', không phải tổng số ban của server. Bản ghi cũ không có
    'source' đều là ban spam trap.
    """
    if not os.path.exists(BAN_LOG_FILE):
        return 0
    seen = set()
    count = 0
    try:
        with open(BAN_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = _json.loads(raw)
                except Exception:
                    count += 1
                    continue
                if rec.get('source') == 'admin':
                    continue
                key = _json.dumps(
                    {k: v for k, v in rec.items() if k != 'time'},
                    sort_keys=True, ensure_ascii=False,
                )
                if key in seen:
                    continue
                seen.add(key)
                count += 1
    except OSError:
        return 0
    return count

async def recount_and_sync_ban_counter():
    """Đặt ban_count = số ban unique trong ban_log.jsonl rồi sync message ở mọi guild."""
    total = count_ban_log_entries()
    state = load_spam_trap_state()
    state["ban_count"] = total
    save_spam_trap_state(state)
    synced = 0
    for guild in bot.guilds:
        try:
            await sync_spam_trap_ban_counter(guild, increment=False)
            synced += 1
        except Exception as e:
            log_event("spam_trap", f"Loi sync ban counter guild {guild.id}: {e}", "warn")
    log_event("spam_trap", f"Recount ban_count = {total} tu ban_log, sync {synced} guild.")
    return total

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
            delete_message_seconds=SPAM_TRAP_BAN_DELETE_SECONDS,
        )
        await update_spam_trap_ban_counter(guild)
        log_event("spam_trap_ban", f"Da ban {author.id}: {reason_text}")
        append_ban_log({
            "source": "spam_trap",
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

@bot.command(name='dlt')
@commands.has_permissions(manage_messages=True)
async def delete_target_keyword_command(ctx, limit: int = 100):
    limit = max(1, min(int(limit or 100), 500))
    await ctx.send(f"Dang quet cac kenh trong TARGET_CATEGORY_IDS, {limit} tin gan nhat moi kenh...")
    result = await delete_target_keyword_messages_in_categories(ctx.guild, limit)
    await ctx.send(result)

@bot.tree.command(name='dlt', description='Quet TARGET_CATEGORY_IDS va xoa tin cua TARGET_USER_ID neu khop keyword')
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(limit='So tin gan nhat can quet moi kenh trong danh muc ap dung, toi da 500')
async def slash_delete_target_keyword_messages(interaction: discord.Interaction, limit: int = 100):
    await interaction.response.defer(thinking=True, ephemeral=True)
    result = await delete_target_keyword_messages_in_categories(interaction.guild, limit)
    await interaction.followup.send(result, ephemeral=True)

@bot.command(name='synccounter', aliases=['recount', 'recountban'])
@commands.has_permissions(manage_messages=True)
async def sync_ban_counter_command(ctx):
    total = await recount_and_sync_ban_counter()
    await ctx.send(f"Da cap nhat 'So mit to bit da ban' = {total} (tinh tu ban_log).")

@bot.tree.command(name='synccounter', description='Tinh lai so ban tu ban_log va cap nhat message bo dem spam trap')
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
async def slash_sync_ban_counter(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    total = await recount_and_sync_ban_counter()
    await interaction.followup.send(
        f"Da cap nhat 'So mit to bit da ban' = {total} (tinh tu ban_log).", ephemeral=True
    )

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

async def find_ban_audit_entry(guild, user):
    """Tìm entry audit log ứng với ban của user, trả về None nếu không tra được.

    Quét vài entry gần nhất thay vì chỉ 1: khi ban nhiều người liên tiếp
    (vd spam trap), entry mới nhất có thể không phải user này.
    """
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target and entry.target.id == user.id:
                return entry
    except Exception:
        pass
    return None

def append_admin_ban_log(guild, user, banned_by, reason):
    member = guild.get_member(user.id)
    roles_snapshot = []
    if isinstance(member, discord.Member):
        roles_snapshot = [
            {"id": str(r.id), "name": r.name}
            for r in member.roles
            if r.id != guild.id
        ]
    append_ban_log({
        "source": "admin",
        "guild_id": str(guild.id),
        "guild_name": guild.name,
        "user_id": str(user.id),
        "username": str(user),
        "display_name": getattr(user, "display_name", None) or str(user),
        "user_created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else "",
        "joined_at": member.joined_at.isoformat() if member and member.joined_at else "",
        "roles_at_ban": roles_snapshot,
        "banned_by_id": str(banned_by.id) if banned_by else "",
        "banned_by_name": str(banned_by) if banned_by else "",
        "reason_text": "Admin ban thu cong",
        "audit_reason": reason or "",
    })

# Sự kiện khi một thành viên bị Ban khỏi server
@bot.event
async def on_member_ban(guild, user):
    entry = await find_ban_audit_entry(guild, user)
    banned_by = entry.user if entry else None
    reason = entry.reason if entry else None

    # Ban do chính bot thực hiện (spam trap) đã được append_ban_log ở ban_spam_trap_suspect.
    # _spam_trap_banning bắt được cả khi bot thiếu quyền View Audit Log.
    by_this_bot = (guild.id, user.id) in _spam_trap_banning or (
        banned_by is not None and bot.user is not None and banned_by.id == bot.user.id
    )
    if not by_this_bot:
        append_admin_ban_log(guild, user, banned_by, reason)
        who = f"{banned_by} ({banned_by.id})" if banned_by else "khong ro"
        log_event("admin_ban", f"Ghi ban log: {user.id} bi ban boi {who}.")

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

                if banned_by:
                    embed.add_field(name="Ban bởi Admin", value=f"{banned_by.mention} (`{banned_by.id}`)", inline=False)
                if reason:
                    embed.add_field(name="Lý do", value=reason, inline=False)

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
