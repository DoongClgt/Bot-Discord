#!/usr/bin/env bash
set -euo pipefail

# Cai dat 2 systemd service (bot + dashboard) + polkit rule, de:
#  - Bot chi chay 1 instance duy nhat (het ban trung do chay 2 tien trinh).
#  - Nut Bat/Tat bot tren dashboard va deploy dieu khien service khong can sudo.
#
# Chay:
#   sudo bash deploy/install_systemd.sh
# Tuy chon chi dinh user chay service:
#   sudo RUN_USER=youruser bash deploy/install_systemd.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Hay chay bang root: sudo bash deploy/install_systemd.sh"
  exit 1
fi

# User chay service: uu tien $RUN_USER, roi $SUDO_USER, roi chu so huu PROJECT_DIR.
RUN_USER="${RUN_USER:-${SUDO_USER:-$(stat -c '%U' "$PROJECT_DIR")}}"
PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "ERROR: khong tim thay $PYTHON"
  echo "Tao venv truoc: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "PROJECT_DIR = $PROJECT_DIR"
echo "RUN_USER    = $RUN_USER"
echo "PYTHON      = $PYTHON"
if [ "$RUN_USER" = "root" ]; then
  echo "Canh bao: service se chay bang root. Nen dung user rieng (RUN_USER=...)."
fi

mkdir -p "$PROJECT_DIR/data"

render() {
  sed -e "s#__PROJECT_DIR__#${PROJECT_DIR}#g" \
      -e "s#__RUN_USER__#${RUN_USER}#g" \
      "$1" > "$2"
}

# 1) Dung tien trinh cu (pid-based) de tranh chay trung voi service moi.
for pidfile in "$PROJECT_DIR/data/bot.pid" "$PROJECT_DIR/data/web.pid"; do
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "Kill tien trinh cu PID $pid ($pidfile)"
      kill "$pid" || true
    fi
    rm -f "$pidfile"
  fi
done

# 2) Ghi unit files.
render "$SCRIPT_DIR/bot-discord-bot.service" /etc/systemd/system/bot-discord-bot.service
render "$SCRIPT_DIR/bot-discord-dashboard.service" /etc/systemd/system/bot-discord-dashboard.service
echo "Da ghi /etc/systemd/system/bot-discord-{bot,dashboard}.service"

# 3) Polkit rule cho RUN_USER dieu khien 2 service khong can mat khau.
mkdir -p /etc/polkit-1/rules.d
render "$SCRIPT_DIR/49-bot-discord.rules" /etc/polkit-1/rules.d/49-bot-discord.rules
echo "Da ghi /etc/polkit-1/rules.d/49-bot-discord.rules"

# 4) Kich hoat.
systemctl daemon-reload
systemctl enable --now bot-discord-bot.service bot-discord-dashboard.service

echo
echo "=== Trang thai ==="
systemctl --no-pager --lines=0 status bot-discord-bot.service bot-discord-dashboard.service || true
echo
echo "Xong. Xem log:"
echo "  journalctl -u bot-discord-bot -f"
echo "  journalctl -u bot-discord-dashboard -f"
echo "  (hoac tail -f $PROJECT_DIR/data/bot_vps.log)"
echo
echo "Luu y: TU GIO KHONG dung deploy/start_vps.sh nua (se tao tien trinh trung)."
