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

read_env_value() {
  local key="$1"
  local value=""
  if [ -f .env ]; then
    value="$(python3 - "$key" <<'PY'
import sys
from pathlib import Path
key = sys.argv[1]
for raw in Path('.env').read_text(encoding='utf-8', errors='ignore').splitlines():
    line = raw.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    name, val = line.split('=', 1)
    if name.strip() == key:
        print(val.strip().strip('"').strip("'"))
        break
PY
)"
  fi
  if [ -z "$value" ]; then
    value="${!key:-}"
  fi
  printf '%s' "$value"
}

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

notify_deploy_success() {
  local status_json="$1"
  local version_json="$2"
  local webhook_url
  webhook_url="$(read_env_value DEPLOY_NOTIFY_WEBHOOK_URL)"
  if [ -z "$webhook_url" ]; then
    log "Deploy notification webhook is not configured."
    return 0
  fi

  local message payload
  message="$(python3 - "$status_json" "$version_json" <<'PY'
import json
import sys
status = json.loads(sys.argv[1] or '{}')
version = json.loads(sys.argv[2] or '{}')
commit = version.get('commit') or 'unknown'
subject = version.get('commit_subject') or 'unknown'
branch = version.get('branch') or 'unknown'
pid = status.get('pid') or 'unknown'
dashboard = version.get('public_url') or 'http://127.0.0.1:5000'
print(
    "✅ **Bot-Discord deploy xong**\n"
    f"- Commit: `{commit}` — {subject}\n"
    f"- Branch: `{branch}`\n"
    f"- Bot PID: `{pid}`\n"
    f"- Dashboard: `{dashboard}`"
)
PY
)"
  payload="{\"content\":$(printf '%s' "$message" | json_escape)}"

  if curl -fsS \
    -H 'Content-Type: application/json' \
    -H 'User-Agent: Bot-Discord-Deploy/1.0' \
    --data "$payload" \
    "$webhook_url" >/dev/null; then
    log "Deploy notification sent."
  else
    log "WARNING: Deploy notification failed."
  fi
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

log "Compile bot.py core.py moderation.py steam.py tickets.py web.py"
python3 -m py_compile bot.py core.py moderation.py steam.py tickets.py web.py

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

status_json="$(curl -fsS http://127.0.0.1:5000/api/status || true)"
version_json="$(curl -fsS http://127.0.0.1:5000/api/version || true)"
log "Status: $status_json"
log "Version: $version_json"
notify_deploy_success "$status_json" "$version_json"
log "Done deploy at $(date -Is)"
