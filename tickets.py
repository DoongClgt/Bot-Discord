"""tickets.py - He thong ticket: view, handler, transcript, lenh panel."""
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

# ===== Ticket system =====

_ticket_create_lock = asyncio.Lock()

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
