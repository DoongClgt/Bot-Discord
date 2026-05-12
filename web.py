from flask import Flask, render_template, jsonify, request, send_file, abort
import datetime
import io
import json
import psutil
import subprocess
import os
import sys
import dotenv
import time
import zipfile

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
ENV_FILE = ".env"
dotenv.load_dotenv(ENV_FILE)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
IPC_CMD_FILE = os.path.join(DATA_DIR, 'ipc_cmd.txt')
IPC_RESPONSE_FILE = os.path.join(DATA_DIR, 'ipc_response.txt')
CHANNELS_FILE = os.path.join(DATA_DIR, 'channels.json')
BOT_EVENTS_FILE = os.path.join(DATA_DIR, 'bot_events.log')
BAN_LOG_FILE = os.path.join(DATA_DIR, 'ban_log.jsonl')
TRANSCRIPT_DIR = os.path.join(DATA_DIR, 'transcripts')
TRANSCRIPT_INDEX_FILE = os.path.join(DATA_DIR, 'transcripts_index.jsonl')
GIVEAWAYS_STATE_FILE = os.path.join(DATA_DIR, 'giveaways.json')
GIVEAWAYS_HISTORY_FILE = os.path.join(DATA_DIR, 'giveaways_history.jsonl')
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
DASHBOARD_PUBLIC_URL = os.getenv("DASHBOARD_PUBLIC_URL", "").strip()
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# File name of the bot to search for
BOT_FILE = "bot.py"
BOT_PATH = os.path.join(APP_ROOT, BOT_FILE)
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == "nt" else 0
_bot_status_cache = {"checked_at": 0, "pid": None}
_metrics_proc_cache = {"pid": None, "proc": None}

def run_git_command(*args):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=APP_ROOT,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()

def get_version_info():
    commit = run_git_command("rev-parse", "--short", "HEAD")
    full_commit = run_git_command("rev-parse", "HEAD")
    branch = run_git_command("branch", "--show-current")
    commit_time = run_git_command("log", "-1", "--format=%cd", "--date=format:%d-%m-%Y %H:%M:%S")
    commit_subject = run_git_command("log", "-1", "--format=%s")
    dirty = bool(run_git_command("status", "--short"))
    return {
        "commit": commit or "unknown",
        "full_commit": full_commit or "",
        "branch": branch or "unknown",
        "commit_time": commit_time or "unknown",
        "commit_subject": commit_subject or "unknown",
        "dirty": dirty,
        "python": sys.version.split()[0],
        "dashboard_host": DASHBOARD_HOST,
        "dashboard_port": DASHBOARD_PORT,
        "public_url": DASHBOARD_PUBLIC_URL,
        "checked_at": datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    }

def is_bot_running(force=False):
    now = time.monotonic()
    if not force and now - _bot_status_cache["checked_at"] < 1.5:
        return _bot_status_cache["pid"]

    found_pid = None
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if Python is running and bot.py is in the command line args
            proc_name = (proc.info.get('name') or '').lower()
            if 'python' in proc_name:
                cmdline = proc.info.get('cmdline') or []
                if any(os.path.abspath(arg) == BOT_PATH or arg.endswith(BOT_FILE) for arg in cmdline):
                    found_pid = proc.info['pid']
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    _bot_status_cache["checked_at"] = now
    _bot_status_cache["pid"] = found_pid
    return found_pid

def start_bot_process():
    proc = subprocess.Popen([sys.executable, BOT_PATH], cwd=os.path.dirname(BOT_PATH), creationflags=CREATE_NO_WINDOW)
    _bot_status_cache["checked_at"] = time.monotonic()
    _bot_status_cache["pid"] = proc.pid
    return proc

def stop_bot_process(pid):
    proc = psutil.Process(pid)
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except psutil.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    _bot_status_cache["checked_at"] = 0
    _bot_status_cache["pid"] = None

def atomic_write_json(path, data):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp_path, path)

def normalize_log_time(value):
    text = str(value or '').strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.datetime.strptime(text, fmt)
            return parsed.strftime("%d-%m-%Y %H:%M:%S" if fmt.endswith("%S") else "%d-%m-%Y %H:%M")
        except ValueError:
            pass
    return text

def read_recent_json_lines(path, limit=100):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-limit:]
    except OSError:
        return []

    items = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            item["time"] = normalize_log_time(item.get("time"))
            items.append(item)
        except json.JSONDecodeError:
            items.append({"time": "", "level": "info", "event": "raw", "message": line})
    return list(reversed(items))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def status():
    pid = is_bot_running()
    if pid:
        return jsonify({"status": "online", "pid": pid})
    return jsonify({"status": "offline"})

@app.route('/api/start', methods=['POST'])
def start_bot():
    if not is_bot_running(force=True):
        try:
            # Start the bot as a background process
            # On Windows, creationflags=subprocess.CREATE_NO_WINDOW can hide the console but we want it detached anyway
            start_bot_process()
            return jsonify({"success": True, "message": "Bot is starting..."})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    return jsonify({"success": False, "message": "Bot is already running."})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    pid = is_bot_running(force=True)
    if pid:
        try:
            stop_bot_process(pid)
            return jsonify({"success": True, "message": "Bot has been stopped."})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    return jsonify({"success": False, "message": "Bot is not running."})

@app.route('/api/config', methods=['GET'])
def get_config():
    config = dotenv.dotenv_values(ENV_FILE)
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def save_config():
    new_config = request.json or {}
    for key, value in new_config.items():
        dotenv.set_key(ENV_FILE, key, str(value))
    
    # Restart bot if running
    pid = is_bot_running(force=True)
    if pid:
        try:
            stop_bot_process(pid)
            time.sleep(1) # Chờ 1 giây để tiến trình tắt hẳn
        except Exception:
            pass
        start_bot_process()
            
    return jsonify({"success": True, "message": "Config saved and bot reloaded!"})

@app.route('/api/command', methods=['POST'])
def send_command():
    payload = request.json or {}
    if not is_bot_running():
        return jsonify({"success": False, "message": "Lỗi: Hãy khởi động Bot (Nút Xanh Lá) trước khi gửi lệnh!"}), 400

    cmd = payload.get('command')
    if not cmd:
        return jsonify({"success": False, "message": "Lệnh không hợp lệ."}), 400
        
    try:
        # Xóa file response cũ nếu có
        ipc_resp = IPC_RESPONSE_FILE
        if os.path.exists(ipc_resp):
            os.remove(ipc_resp)
            
        # Ghi nguyên cụm JSON vào file queue
        atomic_write_json(IPC_CMD_FILE, payload)
            
        # Phản hồi ngay lập tức - bot sẽ tự xử lý ngầm
        return jsonify({"success": True, "message": f"✅ Đã gửi lệnh [{cmd.upper()}] tới Bot! Đang xử lý..."})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi không xác định: {str(e)}"}), 500

@app.route('/api/command_result', methods=['GET'])
def get_command_result():
    """Frontend gọi endpoint này mỗi vài giây để kiểm tra bot đã xử lý xong chưa."""
    ipc_resp = IPC_RESPONSE_FILE
    if os.path.exists(ipc_resp):
        with open(ipc_resp, 'r', encoding='utf-8') as f:
            msg = f.read().strip()
        os.remove(ipc_resp)
        return jsonify({"done": True, "message": msg})
    return jsonify({"done": False})

@app.route('/api/channels', methods=['GET'])
def get_channels():
    """Trả về bản đồ ID → Tên kênh để hiển thị trên Settings."""
    channels_file = CHANNELS_FILE
    if os.path.exists(channels_file):
        try:
            with open(channels_file, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except:
            pass
    return jsonify({})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    limit_raw = request.args.get('limit', '100')
    limit = int(limit_raw) if str(limit_raw).isdigit() else 100
    limit = min(max(limit, 1), 300)
    return jsonify(read_recent_json_lines(BOT_EVENTS_FILE, limit))

@app.route('/api/version', methods=['GET'])
def version():
    return jsonify(get_version_info())

@app.route('/api/deploy', methods=['POST'])
def deploy_webhook():
    expected_token = os.getenv("DEPLOY_WEBHOOK_TOKEN", "").strip()
    if expected_token:
        auth_header = request.headers.get("Authorization", "")
        supplied_token = ""
        if auth_header.startswith("Bearer "):
            supplied_token = auth_header.split(" ", 1)[1].strip()
        if supplied_token != expected_token:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

    script_path = os.path.join(APP_ROOT, "deploy", "deploy_from_webhook.sh")
    if not os.path.exists(script_path):
        return jsonify({"success": False, "message": "Deploy script not found"}), 500

    log_path = os.path.join(DATA_DIR, "deploy_webhook.log")
    with open(log_path, "a", encoding="utf-8") as log_file:
        subprocess.Popen(
            ["bash", script_path],
            cwd=APP_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    return jsonify({"success": True, "message": "Deploy started"}), 202

def get_bot_metrics():
    pid = is_bot_running()
    if not pid:
        _metrics_proc_cache["pid"] = None
        _metrics_proc_cache["proc"] = None
        return {"online": False}

    proc = _metrics_proc_cache["proc"]
    if _metrics_proc_cache["pid"] != pid or proc is None or not proc.is_running():
        try:
            proc = psutil.Process(pid)
            proc.cpu_percent(interval=None)
            _metrics_proc_cache["pid"] = pid
            _metrics_proc_cache["proc"] = proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"online": False}

    try:
        cpu = proc.cpu_percent(interval=None)
        mem = proc.memory_info().rss
        total_mem = psutil.virtual_memory().total
        create_time = proc.create_time()
        threads = proc.num_threads()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {"online": False}

    return {
        "online": True,
        "pid": pid,
        "cpu_percent": round(cpu, 1),
        "rss_bytes": int(mem),
        "rss_mb": round(mem / (1024 * 1024), 1),
        "rss_percent": round(mem / total_mem * 100, 2) if total_mem else 0,
        "uptime_sec": max(0, int(time.time() - create_time)),
        "threads": threads,
        "cpu_count": psutil.cpu_count(logical=True) or 1,
    }

@app.route('/api/metrics', methods=['GET'])
def metrics():
    return jsonify(get_bot_metrics())

@app.route('/api/ban_log', methods=['GET'])
def ban_log_list():
    limit_raw = request.args.get('limit', '200')
    limit = int(limit_raw) if str(limit_raw).isdigit() else 200
    limit = min(max(limit, 1), 1000)
    if not os.path.exists(BAN_LOG_FILE):
        return jsonify({"count": 0, "items": []})
    try:
        with open(BAN_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except OSError:
        return jsonify({"count": 0, "items": []})

    items = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            items.append({"time": "", "raw": line})
    items.reverse()
    return jsonify({"count": len(items), "total_lines": len(lines), "items": items})

@app.route('/api/tickets/transcripts', methods=['GET'])
def tickets_transcripts_list():
    if not os.path.exists(TRANSCRIPT_INDEX_FILE):
        return jsonify({"count": 0, "items": []})
    try:
        with open(TRANSCRIPT_INDEX_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except OSError:
        return jsonify({"count": 0, "items": []})

    items = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    items.reverse()
    return jsonify({"count": len(items), "items": items})


@app.route('/api/tickets/transcripts/download_all', methods=['GET'])
def tickets_transcripts_download_all():
    if not os.path.isdir(TRANSCRIPT_DIR):
        return jsonify({"success": False, "message": "Chưa có transcript nào."}), 404
    files = sorted(f for f in os.listdir(TRANSCRIPT_DIR) if f.endswith('.txt'))
    if not files and not os.path.exists(TRANSCRIPT_INDEX_FILE):
        return jsonify({"success": False, "message": "Chưa có transcript nào."}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in files:
            fpath = os.path.join(TRANSCRIPT_DIR, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, arcname=f"transcripts/{fname}")
        if os.path.exists(TRANSCRIPT_INDEX_FILE):
            zf.write(TRANSCRIPT_INDEX_FILE, arcname='transcripts_index.jsonl')
    buf.seek(0)

    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'transcripts-{ts}.zip',
    )


@app.route('/api/tickets/transcripts/<path:filename>', methods=['GET'])
def tickets_transcript_download(filename):
    # Cách ly thư mục, không cho path traversal
    safe = os.path.basename(filename)
    file_path = os.path.join(TRANSCRIPT_DIR, safe)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        abort(404)
    return send_file(
        file_path,
        mimetype='text/plain; charset=utf-8',
        as_attachment=True,
        download_name=safe,
    )


@app.route('/api/giveaways', methods=['GET'])
def giveaways_list():
    active = []
    ended = []
    if os.path.exists(GIVEAWAYS_STATE_FILE):
        try:
            with open(GIVEAWAYS_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except (OSError, json.JSONDecodeError):
            state = {}
        for mid, gw in state.items():
            gw = dict(gw)
            gw['message_id'] = mid
            gw['entrants_count'] = len(gw.get('entrants', []))
            gw.pop('entrants', None)  # bớt payload
            if gw.get('ended') or gw.get('cancelled'):
                ended.append(gw)
            else:
                active.append(gw)
    active.sort(key=lambda g: g.get('ends_at_unix', 0))
    ended.sort(key=lambda g: g.get('ended_at_unix', 0), reverse=True)
    return jsonify({"active": active, "ended": ended[:50]})


@app.route('/api/giveaways/start', methods=['POST'])
def giveaways_start():
    payload = request.json or {}
    prize = str(payload.get('prize', '') or '').strip()
    duration = str(payload.get('duration', '') or '').strip()
    description = str(payload.get('description', '') or '').strip()
    channel_id = str(payload.get('channel_id', '') or '').strip()
    required_role_id = str(payload.get('required_role_id', '') or '').strip()
    ping_target = str(payload.get('ping_target', '') or '').strip()
    try:
        winners = max(1, min(50, int(payload.get('winners', 1) or 1)))
    except (ValueError, TypeError):
        winners = 1

    if not prize:
        return jsonify({"success": False, "message": "Thiếu phần thưởng."}), 400
    if not duration:
        return jsonify({"success": False, "message": "Thiếu thời lượng."}), 400
    if not channel_id.isdigit():
        return jsonify({"success": False, "message": "Kênh không hợp lệ."}), 400
    if required_role_id and not required_role_id.isdigit():
        return jsonify({"success": False, "message": "Vai trò yêu cầu không hợp lệ."}), 400
    if ping_target and ping_target not in ("everyone", "here") and not ping_target.isdigit():
        return jsonify({"success": False, "message": "Tùy chọn ping không hợp lệ."}), 400
    if not is_bot_running():
        return jsonify({"success": False, "message": "Bot chưa chạy, không gửi được lệnh."}), 400

    if os.path.exists(IPC_RESPONSE_FILE):
        try:
            os.remove(IPC_RESPONSE_FILE)
        except OSError:
            pass
    atomic_write_json(IPC_CMD_FILE, {
        "command": "giveaway_start",
        "args": {
            "prize": prize,
            "duration": duration,
            "winners": winners,
            "description": description,
            "channel_id": channel_id,
            "required_role_id": required_role_id,
            "ping_target": ping_target,
        },
    })
    return jsonify({"success": True, "message": "Đã gửi lệnh tạo đợt quay thưởng."})


@app.route('/api/giveaways/end', methods=['POST'])
def giveaways_end():
    payload = request.json or {}
    mid = str(payload.get('message_id', '')).strip()
    if not mid.isdigit():
        return jsonify({"success": False, "message": "Message ID phải là số."}), 400
    if not is_bot_running():
        return jsonify({"success": False, "message": "Bot chưa chạy, không gửi được lệnh."}), 400
    if os.path.exists(IPC_RESPONSE_FILE):
        try:
            os.remove(IPC_RESPONSE_FILE)
        except OSError:
            pass
    atomic_write_json(IPC_CMD_FILE, {"command": "giveaway_end", "args": {"message_id": mid}})
    return jsonify({"success": True, "message": "Đã gửi lệnh end."})


@app.route('/api/giveaways/reroll', methods=['POST'])
def giveaways_reroll():
    payload = request.json or {}
    mid = str(payload.get('message_id', '')).strip()
    count = int(payload.get('count', 1) or 1)
    if not mid.isdigit():
        return jsonify({"success": False, "message": "Message ID phải là số."}), 400
    if not is_bot_running():
        return jsonify({"success": False, "message": "Bot chưa chạy, không gửi được lệnh."}), 400
    if os.path.exists(IPC_RESPONSE_FILE):
        try:
            os.remove(IPC_RESPONSE_FILE)
        except OSError:
            pass
    atomic_write_json(IPC_CMD_FILE, {"command": "giveaway_reroll", "args": {"message_id": mid, "count": count}})
    return jsonify({"success": True, "message": "Đã gửi lệnh reroll."})


@app.route('/api/ban_log/download', methods=['GET'])
def ban_log_download():
    if not os.path.exists(BAN_LOG_FILE):
        return jsonify({"success": False, "message": "Chưa có ban nào để tải."}), 404
    return send_file(
        BAN_LOG_FILE,
        mimetype='application/x-ndjson',
        as_attachment=True,
        download_name='ban_log.jsonl',
    )

if __name__ == '__main__':
    local_url = f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"

    print("========================================")
    print("Web dashboard started")
    print(f"Local URL: {local_url}")
    if DASHBOARD_PUBLIC_URL:
        print(f"Public URL: {DASHBOARD_PUBLIC_URL}")
    print("Cloudflare Tunnel target should point to the local URL above.")
    print("========================================")

    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)
