#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/data/deploy_webhook.log"

mkdir -p "$PROJECT_DIR/data"
cd "$PROJECT_DIR"

log() {
  printf '[deploy-webhook] %s\n' "$*" | tee -a "$LOG_FILE"
}

log "Start deploy at $(date -Is)"
log "Project: $PROJECT_DIR"

log "Fetching origin"
git fetch origin

log "Reset to origin/main"
git reset --hard origin/main

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  log "ERROR: .venv not found"
  exit 1
fi

log "Compile bot.py web.py"
python3 -m py_compile bot.py web.py

log "Stop existing bot/dashboard"
for pidfile in data/bot.pid data/web.pid; do
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
    fi
  fi
done
sleep 3

log "Start bot/dashboard"
bash deploy/start_vps.sh >> "$LOG_FILE" 2>&1
sleep 5

log "Status: $(curl -fsS http://127.0.0.1:5000/api/status || true)"
log "Version: $(curl -fsS http://127.0.0.1:5000/api/version || true)"
log "Done deploy at $(date -Is)"
