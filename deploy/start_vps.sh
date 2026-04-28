#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"
mkdir -p data

if [ ! -f ".venv/bin/activate" ]; then
  echo "Khong tim thay .venv. Hay chay:"
  echo "python3 -m venv .venv"
  echo "source .venv/bin/activate"
  echo "pip install -r requirements.txt"
  exit 1
fi

source .venv/bin/activate

if [ ! -f ".env" ]; then
  echo "Khong tim thay .env. Hay chay: cp .env.example .env && nano .env"
  exit 1
fi

nohup python3 bot.py >> data/bot_vps.log 2>&1 &
echo "$!" > data/bot.pid
echo "Bot dang chay, PID: $(cat data/bot.pid)"

nohup python3 web.py >> data/web_vps.log 2>&1 &
echo "$!" > data/web.pid
echo "Dashboard dang chay, PID: $(cat data/web.pid)"

echo "Dashboard local: http://127.0.0.1:5000"
echo "Xem log: tail -f data/bot_vps.log data/web_vps.log"
