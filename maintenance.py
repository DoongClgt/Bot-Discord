"""maintenance.py - Bao tri VPS tu trong bot: rotate log stdout, don file .tmp sot, canh bao o day.

User khong SSH vao VPS duoc, nen moi viec don dep phai do bot tu lam.
"""
import asyncio
import os
import shutil
import time

from discord.ext import tasks

from core import DATA_DIR, GENERAL_LOG_CHANNEL_ID, log_event, send_general_log


# stdout/stderr cua systemd (StandardOutput=append:) va start_vps.sh (>>) ghi noi vao cac file nay,
# khong co gi don. Ca 2 kieu deu mo file voi O_APPEND nen truncate tai cho la an toan:
# lan ghi tiep theo cua tien trinh kia tu nhay ve cuoi file moi (khong tao lo hong).
ROTATED_LOG_FILES = [
    os.path.join(DATA_DIR, name)
    for name in ('bot_vps.log', 'web_vps.log', 'deploy_webhook.log')
]
VPS_LOG_MAX_MB_RAW = os.getenv('VPS_LOG_MAX_MB', '20').strip()
VPS_LOG_MAX_MB = int(VPS_LOG_MAX_MB_RAW) if VPS_LOG_MAX_MB_RAW.isdigit() else 20
VPS_LOG_MAX_MB = min(max(VPS_LOG_MAX_MB, 1), 1024)
# Chi giu phan cuoi sang .1 (khong copy ca file): file co the da phinh toi hang GB.
VPS_LOG_KEEP_TAIL_BYTES = 1024 * 1024

# .tmp cua atomic_write_* chi ton tai vai ms; con nam lai qua lau tuc la lan ghi do da chet giua chung
# (vd o day). Nguong 10 phut de khong xoa nham .tmp ma web.py dang ghi do.
STALE_TMP_SECONDS = 600

# DISK_FREE_WARN_GB=0 -> tat canh bao.
DISK_FREE_WARN_GB_RAW = os.getenv('DISK_FREE_WARN_GB', '5').strip()
DISK_FREE_WARN_GB = int(DISK_FREE_WARN_GB_RAW) if DISK_FREE_WARN_GB_RAW.isdigit() else 5
DISK_ALERT_REPEAT_SECONDS = 6 * 3600
MAINTENANCE_INTERVAL_MINUTES = 10

_last_disk_alert_at = 0.0

def rotate_log_if_needed(path, max_bytes):
    try:
        size = os.path.getsize(path)
    except OSError:
        return False
    if size < max_bytes:
        return False

    backup = f"{path}.1"
    try:
        # Xoa ban .1 cu truoc de co cho trong khi o sap day
        os.remove(backup)
    except OSError:
        pass
    try:
        with open(path, 'rb') as src:
            src.seek(max(0, size - VPS_LOG_KEEP_TAIL_BYTES))
            tail = src.read()
        with open(backup, 'wb') as dst:
            dst.write(tail)
    except OSError:
        # Khong luu duoc phan cuoi (o day) -> bo .1 do dang, van truncate de giai phong cho
        try:
            os.remove(backup)
        except OSError:
            pass
    with open(path, 'r+b') as f:
        f.truncate(0)
    return True

def cleanup_stale_tmp_files():
    removed = []
    now = time.time()
    try:
        entries = list(os.scandir(DATA_DIR))
    except OSError:
        return removed
    for entry in entries:
        if not entry.name.endswith('.tmp'):
            continue
        try:
            if entry.is_file() and now - entry.stat().st_mtime >= STALE_TMP_SECONDS:
                os.remove(entry.path)
                removed.append(entry.name)
        except OSError:
            pass
    return removed

def rotate_and_cleanup():
    max_bytes = VPS_LOG_MAX_MB * 1024 * 1024
    for path in ROTATED_LOG_FILES:
        try:
            if rotate_log_if_needed(path, max_bytes):
                log_event("maintenance", f"Da rotate {os.path.basename(path)} (vuot {VPS_LOG_MAX_MB} MB).")
        except OSError as e:
            log_event("maintenance", f"Khong rotate duoc {os.path.basename(path)}: {e}", "error")

    removed = cleanup_stale_tmp_files()
    if removed:
        log_event("maintenance", f"Da xoa file .tmp sot: {', '.join(removed)}.")

async def check_disk_space():
    global _last_disk_alert_at
    if not DISK_FREE_WARN_GB:
        return

    usage = shutil.disk_usage(DATA_DIR)
    free_gb = usage.free / 1024 ** 3
    total_gb = usage.total / 1024 ** 3
    if free_gb >= DISK_FREE_WARN_GB:
        if _last_disk_alert_at:
            _last_disk_alert_at = 0.0
            log_event("maintenance", f"O dia da on lai: con {free_gb:.1f} GB trong.")
        return

    now = time.monotonic()
    if _last_disk_alert_at and now - _last_disk_alert_at < DISK_ALERT_REPEAT_SECONDS:
        return
    _last_disk_alert_at = now

    used_percent = round(usage.used / usage.total * 100) if usage.total else 0
    log_event("maintenance", f"O dia sap day: con {free_gb:.1f}/{total_gb:.0f} GB ({used_percent}% da dung).", "warn")
    print(f"Maintenance: o dia sap day, con {free_gb:.1f} GB.")
    if GENERAL_LOG_CHANNEL_ID:
        await send_general_log(None, (
            f"⚠️ **Ổ đĩa VPS sắp đầy**: còn `{free_gb:.1f} GB` / `{total_gb:.0f} GB` ({used_percent}% đã dùng).\n"
            "Mở dashboard → trang **Version** → *Dung lượng ổ đĩa* để xem thư mục/file nào lớn."
        ))

@tasks.loop(minutes=MAINTENANCE_INTERVAL_MINUTES)
async def vps_maintenance_loop():
    # Bat het exception: OSError lot ra ngoai se bi tasks.loop (reconnect=True) nuot im lang.
    try:
        await asyncio.to_thread(rotate_and_cleanup)
        await check_disk_space()
    except Exception as e:
        log_event("maintenance", f"Loi bao tri: {e!r}", "error")
