from flask import Flask, render_template, jsonify, request
import datetime
import json
import psutil
import subprocess
import os
import sys
import dotenv
import time

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
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
DASHBOARD_PUBLIC_URL = os.getenv("DASHBOARD_PUBLIC_URL", "").strip()
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# File name of the bot to search for
BOT_FILE = "bot.py"
BOT_PATH = os.path.join(APP_ROOT, BOT_FILE)
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == "nt" else 0
_bot_status_cache = {"checked_at": 0, "pid": None}

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
