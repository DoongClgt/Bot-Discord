"""downloader.py - Tai video/anh TikTok & Douyin khong logo, gui vao kenh Discord.

Logic goi API tikwm nam o tiktok_api.py (dung chung voi dashboard web.py).
Dang ky 2 lenh /tiktok (prefix + slash), alias douyin/tt/dl.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import io

from core import bot, log_event
from tiktok_api import http_get, fetch_media_info, extract_media, find_url, safe_filename_base

# Fallback khi khong lay duoc gioi han upload cua server (server chua boost = 10MB)
DEFAULT_FILESIZE_LIMIT = 10 * 1024 * 1024


def _build_caption(media):
    parts = []
    if media["title"]:
        parts.append(f"**{media['title']}**")
    if media["author"]:
        parts.append(f"👤 {media['author']}")
    caption = "\n".join(parts)
    if len(caption) > 1800:
        caption = caption[:1797] + "..."
    return caption


async def resolve_and_send(target, source_url, filesize_limit):
    """Tai media tu source_url va gui vao target (channel hoac followup webhook)."""
    data = await asyncio.to_thread(fetch_media_info, source_url)
    media = extract_media(data)
    caption = _build_caption(media)
    name_base = safe_filename_base(media, source_url)

    # Slideshow anh
    if media["is_slideshow"]:
        files = []
        for idx, img_url in enumerate(media["images"], 1):
            try:
                content = await asyncio.to_thread(http_get, img_url)
            except Exception:
                continue
            if len(content) <= filesize_limit:
                files.append(discord.File(io.BytesIO(content), filename=f"{name_base}_{idx}.jpg"))
        if files:
            await target.send(content=caption or None, files=files)
            return
        links = "\n".join(media["images"])
        await target.send(
            (caption + "\n" if caption else "") + f"⚠️ Khong tai truc tiep anh duoc. Link:\n{links}"
        )
        return

    # Video
    video_url = media["video_url"]
    if not video_url:
        raise RuntimeError("Khong tim thay link tai cho URL nay.")
    content = await asyncio.to_thread(http_get, video_url)
    if len(content) <= filesize_limit:
        file = discord.File(io.BytesIO(content), filename=f"{name_base}.mp4")
        await target.send(content=caption or None, file=file)
    else:
        mb = len(content) / (1024 * 1024)
        await target.send(
            (caption + "\n" if caption else "")
            + f"⚠️ Video {mb:.1f}MB vuot gioi han upload cua server. Link tai truc tiep:\n{video_url}"
        )


@bot.command(name='tiktok', aliases=['douyin', 'tt', 'dl'])
async def tiktok_command(ctx, *, url: str = None):
    source = find_url(url)
    if not source:
        await ctx.send("Dung: `/tiktok <link TikTok hoac Douyin>`")
        return
    limit = ctx.guild.filesize_limit if ctx.guild else DEFAULT_FILESIZE_LIMIT
    async with ctx.typing():
        try:
            await resolve_and_send(ctx.channel, source, limit)
            log_event("downloader", f"Tai TikTok/Douyin OK: {source}")
        except Exception as e:
            log_event("downloader", f"Loi tai {source}: {e}", level="error")
            await ctx.send(f"Khong tai duoc: {e}")


@bot.tree.command(name='tiktok', description='Tai video/anh TikTok hoac Douyin khong logo')
@app_commands.describe(url='Link TikTok hoac Douyin')
async def slash_tiktok(interaction: discord.Interaction, url: str):
    source = find_url(url)
    if not source:
        await interaction.response.send_message(
            "Link khong hop le. Can link TikTok hoac Douyin.", ephemeral=True
        )
        return
    await interaction.response.defer(thinking=True)
    limit = interaction.guild.filesize_limit if interaction.guild else DEFAULT_FILESIZE_LIMIT
    try:
        await resolve_and_send(interaction.followup, source, limit)
        log_event("downloader", f"Tai TikTok/Douyin OK (slash): {source}")
    except Exception as e:
        log_event("downloader", f"Loi tai {source}: {e}", level="error")
        await interaction.followup.send(f"Khong tai duoc: {e}")
