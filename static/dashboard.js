// Dashboard logic — Discord-themed, sidebar layout.
// Talks to Flask endpoints exposed by web.py.

(() => {
    "use strict";

    const els = {
        sidebarStatus: document.getElementById("sidebarStatus"),
        sidebarStatusText: document.getElementById("sidebarStatusText"),
        topStatusPill: document.getElementById("topStatusPill"),
        topStatusText: document.getElementById("topStatusText"),
        topPid: document.getElementById("topPid"),
        btnStart: document.getElementById("btnStart"),
        btnStop: document.getElementById("btnStop"),
        pageTitle: document.getElementById("pageTitle"),
        pageSubtitle: document.getElementById("pageSubtitle"),
        // metrics
        metricStatus: document.getElementById("metricStatus"),
        metricPid: document.getElementById("metricPid"),
        metricChannels: document.getElementById("metricChannels"),
        metricUptime: document.getElementById("metricUptime"),
        // chart
        cpuValue: document.getElementById("cpuValue"),
        ramValue: document.getElementById("ramValue"),
        cpuSparkline: document.getElementById("cpuSparkline"),
        ramSparkline: document.getElementById("ramSparkline"),
        // toast
        toastStack: document.getElementById("toastStack"),
        // modal
        envModal: document.getElementById("envModal"),
        envModalBody: document.getElementById("envModalBody"),
    };

    const PAGE_META = {
        dashboard: { title: "Tổng quan", subtitle: "Trạng thái và tác vụ nhanh" },
        settings: { title: "Cấu hình", subtitle: "Token, keywords, kênh áp dụng" },
        steam: { title: "Steam Watcher", subtitle: "Theo dõi patch trên Steam" },
        logs: { title: "Log gần đây", subtitle: "Sự kiện mới nhất từ bot" },
        banlog: { title: "Ban log", subtitle: "Lịch sử ban từ spam trap và admin, có thể tải về" },
        tickets: { title: "Tickets", subtitle: "Transcript ticket đã đóng, có thể tải về" },
        version: { title: "Version", subtitle: "Thông tin commit và môi trường" },
    };

    const SPARK_BUFFER = 60;
    const cpuBuffer = [];
    const ramBuffer = [];

    let channelMap = {};
    let lastConfig = {};
    let commandPollTimer = null;
    let currentPage = "dashboard";
    let lastCpuPercent = 0;
    let lastRamMb = 0;
    let lastCpuCount = 1;

    /* ── Toast ─────────────────────────────────────────────── */

    const ICONS = {
        info: '<svg viewBox="0 0 16 16" fill="currentColor" width="18" height="18"><path d="M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zm.75 9.75a.75.75 0 0 1-1.5 0v-3.5a.75.75 0 0 1 1.5 0v3.5zM8 6.25a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8z"/></svg>',
        success: '<svg viewBox="0 0 16 16" fill="currentColor" width="18" height="18"><path d="M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM6.97 11.03 3.94 8 5 6.94l1.97 1.97L11 4.94 12.06 6l-5.09 5.03z"/></svg>',
        error: '<svg viewBox="0 0 16 16" fill="currentColor" width="18" height="18"><path d="M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM5.7 5.7 8 8l2.3-2.3 1.06 1.06L9.06 9.06l2.3 2.3-1.06 1.06L8 10.12 5.7 12.42 4.64 11.36 6.94 9.06l-2.3-2.3L5.7 5.7z"/></svg>',
        warning: '<svg viewBox="0 0 16 16" fill="currentColor" width="18" height="18"><path d="M8 1.5 14.93 13H1.07L8 1.5zm-.75 4.25v3.5h1.5v-3.5h-1.5zm0 4.5v1.5h1.5v-1.5h-1.5z"/></svg>',
    };

    function showToast(message, level = "info", title) {
        if (!els.toastStack || !message) return;
        const t = document.createElement("div");
        t.className = "toast " + level;
        const titleHtml = title ? `<div class="toast-title">${escapeHtml(title)}</div>` : "";
        t.innerHTML = `
            <div class="toast-icon">${ICONS[level] || ICONS.info}</div>
            <div>
                ${titleHtml}
                <div class="toast-msg">${escapeHtml(message)}</div>
            </div>
        `;
        els.toastStack.appendChild(t);
        requestAnimationFrame(() => t.classList.add("show"));
        const lifetime = level === "error" ? 6500 : 4000;
        setTimeout(() => {
            t.classList.remove("show");
            setTimeout(() => t.remove(), 300);
        }, lifetime);
    }

    function escapeHtml(s) {
        return String(s ?? "").replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        }[c]));
    }

    function notify(message, level) {
        // legacy alias
        showToast(message, level || "info");
    }

    /* ── Sidebar nav ───────────────────────────────────────── */

    function activatePage(page) {
        currentPage = page;
        document.querySelectorAll(".nav-item").forEach((b) => {
            b.classList.toggle("active", b.dataset.page === page);
        });
        document.querySelectorAll(".page").forEach((p) => {
            p.classList.toggle("active", p.id === "page-" + page);
        });
        const meta = PAGE_META[page] || {};
        if (els.pageTitle) els.pageTitle.textContent = meta.title || "";
        if (els.pageSubtitle) els.pageSubtitle.textContent = meta.subtitle || "";

        if (page === "logs") loadLogs();
        if (page === "version") loadVersion();
        if (page === "banlog") loadBanLog();
        if (page === "tickets") loadTickets();
    }

    function bindNav() {
        document.querySelectorAll(".nav-item").forEach((btn) => {
            btn.addEventListener("click", () => activatePage(btn.dataset.page));
        });
    }

    function bindSettingsTabs() {
        document.querySelectorAll("[data-settings-tab]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const id = btn.dataset.settingsTab;
                document.querySelectorAll("[data-settings-tab]").forEach((b) => {
                    b.classList.toggle("active", b.dataset.settingsTab === id);
                });
                document.querySelectorAll("[data-settings-panel]").forEach((p) => {
                    p.classList.toggle("active", p.dataset.settingsPanel === id);
                });
            });
        });
    }

    /* ── Status ───────────────────────────────────────────── */

    function applyStatus(state, pid) {
        const online = state === "online";
        const disconnected = state === "disconnected";
        const cls = online ? "online" : disconnected ? "disconnected" : "offline";
        const label = online ? "Online" : disconnected ? "Mất kết nối" : "Offline";

        if (els.topStatusPill) els.topStatusPill.className = "status-pill " + cls;
        if (els.topStatusText) els.topStatusText.textContent = label;
        if (els.topPid) els.topPid.textContent = "PID: " + (pid || "-");

        if (els.sidebarStatus) els.sidebarStatus.className = "sidebar-footer " + cls;
        if (els.sidebarStatusText) els.sidebarStatusText.textContent = label;

        if (els.metricStatus) els.metricStatus.textContent = label;
        if (els.metricPid) els.metricPid.textContent = pid || "-";

        if (els.btnStart) els.btnStart.disabled = online;
        if (els.btnStop) els.btnStop.disabled = !online;
    }

    async function fetchStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            applyStatus(data.status, data.pid || "-");
        } catch {
            applyStatus("disconnected", "-");
        }
    }

    /* ── Bot lifecycle ────────────────────────────────────── */

    async function startBot() {
        if (els.btnStart) els.btnStart.disabled = true;
        showToast("Đang khởi động bot...", "info");
        try {
            const res = await fetch("/api/start", { method: "POST" });
            const data = await res.json();
            showToast(data.message, data.success ? "success" : "warning");
            setTimeout(fetchStatus, 1500);
        } catch {
            showToast("Không gửi được lệnh bật bot.", "error");
            if (els.btnStart) els.btnStart.disabled = false;
        }
    }

    async function stopBot() {
        if (els.btnStop) els.btnStop.disabled = true;
        showToast("Đang tắt bot...", "info");
        try {
            const res = await fetch("/api/stop", { method: "POST" });
            const data = await res.json();
            showToast(data.message, data.success ? "success" : "warning");
            setTimeout(fetchStatus, 1200);
        } catch {
            showToast("Không gửi được lệnh tắt bot.", "error");
            if (els.btnStop) els.btnStop.disabled = false;
        }
    }

    /* ── Metrics + sparkline ──────────────────────────────── */

    function pushSpark(buffer, value) {
        buffer.push(value);
        while (buffer.length > SPARK_BUFFER) buffer.shift();
    }

    function renderSpark(svg, buffer, max) {
        if (!svg) return;
        const w = svg.clientWidth || 200;
        const h = svg.clientHeight || 56;
        svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
        const data = buffer.slice();
        while (data.length < SPARK_BUFFER) data.unshift(0);
        const stepX = w / Math.max(1, data.length - 1);
        const cap = Math.max(max || 1, ...data, 1);
        const points = data.map((v, i) => {
            const x = i * stepX;
            const y = h - (v / cap) * (h - 4) - 2;
            return [x, y];
        });
        const linePath = points.map(([x, y], i) => (i === 0 ? `M${x},${y}` : `L${x},${y}`)).join(" ");
        const areaPath = `${linePath} L${w},${h} L0,${h} Z`;
        svg.innerHTML = `
            <path class="area" d="${areaPath}" />
            <path class="line" d="${linePath}" />
        `;
    }

    function formatUptime(sec) {
        if (!Number.isFinite(sec) || sec <= 0) return "-";
        const d = Math.floor(sec / 86400);
        const h = Math.floor((sec % 86400) / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = Math.floor(sec % 60);
        if (d) return `${d}d ${h}h`;
        if (h) return `${h}h ${m}m`;
        if (m) return `${m}m ${s}s`;
        return `${s}s`;
    }

    async function fetchMetrics() {
        try {
            const res = await fetch("/api/metrics");
            const m = await res.json();
            if (m.online) {
                lastCpuPercent = m.cpu_percent || 0;
                lastRamMb = m.rss_mb || 0;
                lastCpuCount = m.cpu_count || 1;
                pushSpark(cpuBuffer, lastCpuPercent);
                pushSpark(ramBuffer, lastRamMb);
                if (els.cpuValue) els.cpuValue.textContent = `${lastCpuPercent.toFixed(1)}%`;
                if (els.ramValue) els.ramValue.textContent = `${lastRamMb.toFixed(1)} MB`;
                if (els.metricUptime) els.metricUptime.textContent = formatUptime(m.uptime_sec);
            } else {
                pushSpark(cpuBuffer, 0);
                pushSpark(ramBuffer, 0);
                if (els.cpuValue) els.cpuValue.textContent = "-";
                if (els.ramValue) els.ramValue.textContent = "-";
                if (els.metricUptime) els.metricUptime.textContent = "-";
            }
            renderSpark(els.cpuSparkline, cpuBuffer, Math.max(100, lastCpuCount * 100));
            renderSpark(els.ramSparkline, ramBuffer);
        } catch {
            // silent
        }
    }

    /* ── Channels ─────────────────────────────────────────── */

    async function loadChannels() {
        try {
            const res = await fetch("/api/channels");
            channelMap = await res.json();
            if (els.metricChannels) els.metricChannels.textContent = Object.keys(channelMap).length;
        } catch {
            channelMap = {};
            if (els.metricChannels) els.metricChannels.textContent = "-";
        }
    }

    function closeModal(modal) {
        if (modal) modal.classList.remove("show");
    }

    async function openEnvModal() {
        if (!els.envModal || !els.envModalBody) return;
        try {
            const res = await fetch("/api/config");
            const cfg = await res.json();
            const keys = Object.keys(cfg).sort();
            els.envModalBody.innerHTML = keys
                .map((k) => {
                    const isSecret = /TOKEN|SECRET|PASSWORD|KEY/i.test(k);
                    const v = isSecret && cfg[k] ? "•".repeat(8) + " (ẩn)" : cfg[k] || "";
                    return `<div class="kv-row"><span class="k">${escapeHtml(k)}</span><span class="v">${escapeHtml(v)}</span></div>`;
                })
                .join("");
            els.envModal.classList.add("show");
        } catch {
            showToast("Không tải được .env.", "error");
        }
    }

    /* ── Commands (IPC) ───────────────────────────────────── */

    function setButtonBusy(id, busy, label) {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.disabled = busy;
        if (label) {
            if (!btn.dataset.originalText) btn.dataset.originalText = btn.textContent;
            btn.textContent = busy ? label : btn.dataset.originalText;
        }
    }

    async function postCommand(command, args) {
        const res = await fetch("/api/command", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command, args: args || {} }),
        });
        const data = await res.json();
        showToast(data.message, data.success ? "success" : "warning");
        if (!res.ok || !data.success) {
            throw new Error(data.message || "Command failed");
        }
        return data;
    }

    function pollCommandResult(onDone) {
        clearInterval(commandPollTimer);
        commandPollTimer = setInterval(async () => {
            try {
                const res = await fetch("/api/command_result");
                const data = await res.json();
                if (data.done) {
                    clearInterval(commandPollTimer);
                    showToast(data.message, "success");
                    if (onDone) onDone(data.message);
                }
            } catch (err) {
                clearInterval(commandPollTimer);
                if (onDone) onDone(null, err);
            }
        }, 2500);
    }

    async function sendSteamDBCheck() {
        setButtonBusy("btnSteamDB", true, "Đang check...");
        try {
            await postCommand("steamdb_check");
            pollCommandResult(() => setButtonBusy("btnSteamDB", false));
        } catch {
            setButtonBusy("btnSteamDB", false);
        }
    }

    async function sendRecountBanCounter() {
        setButtonBusy("btnRecountBan", true, "Đang tính...");
        try {
            await postCommand("recount_ban_counter");
            pollCommandResult(async () => {
                await loadBanLog();
                setButtonBusy("btnRecountBan", false);
            });
        } catch {
            setButtonBusy("btnRecountBan", false);
        }
    }

    async function sendRefreshChannels() {
        setButtonBusy("btnRefreshChannels", true, "Đang quét...");
        try {
            await postCommand("refresh_channels");
            pollCommandResult(async () => {
                await loadChannels();
                renderReadOnlyDisplays();
                refreshMultiPickers();
                setButtonBusy("btnRefreshChannels", false);
            });
        } catch {
            setButtonBusy("btnRefreshChannels", false);
        }
    }

    /* ── Logs ─────────────────────────────────────────────── */

    function setTextCell(row, text, className) {
        const td = document.createElement("td");
        if (className) td.className = className;
        td.textContent = text || "";
        row.appendChild(td);
        return td;
    }

    async function loadLogs() {
        const body = document.getElementById("logTableBody");
        if (!body) return;
        try {
            const res = await fetch("/api/logs?limit=100");
            const logs = await res.json();
            body.innerHTML = "";
            if (!logs.length) {
                body.innerHTML = '<tr><td colspan="4" class="readonly-empty">Chưa có log.</td></tr>';
                return;
            }
            logs.forEach((item) => {
                const row = document.createElement("tr");
                setTextCell(row, item.time || "-");
                const lvlCell = document.createElement("td");
                const badge = document.createElement("span");
                const level = String(item.level || "info").toLowerCase();
                badge.className = "log-level " + level;
                badge.textContent = level;
                lvlCell.appendChild(badge);
                row.appendChild(lvlCell);
                setTextCell(row, item.event || "-");
                setTextCell(row, item.message || "", "log-message");
                body.appendChild(row);
            });
        } catch {
            body.innerHTML = '<tr><td colspan="4" class="readonly-empty">Không tải được log.</td></tr>';
        }
    }

    /* ── Ban log ──────────────────────────────────────────── */

    async function loadBanLog() {
        const body = document.getElementById("banLogTableBody");
        const total = document.getElementById("banLogTotal");
        if (!body) return;
        try {
            const res = await fetch("/api/ban_log?limit=5000");
            const data = await res.json();
            const items = data.items || [];
            if (total) {
                if (!data.total_lines) {
                    total.textContent = "";
                } else if (items.length >= data.total_lines) {
                    total.textContent = `${data.total_lines} ban tổng, hiển thị tất cả`;
                } else {
                    total.textContent = `${data.total_lines} ban tổng, hiển thị ${items.length} gần nhất`;
                }
            }
            body.innerHTML = "";
            if (!items.length) {
                body.innerHTML = '<tr><td colspan="5" class="readonly-empty">Chưa có ban nào.</td></tr>';
                return;
            }
            items.forEach((it) => {
                const row = document.createElement("tr");
                setTextCell(row, it.time || "-");
                const userText = it.username
                    ? `${it.username}\n${it.user_id || ""}`
                    : it.user_id || "-";
                setTextCell(row, userText, "log-message");
                // Bản ghi cũ không có 'source' đều là ban spam trap.
                const sourceText = it.source === "admin"
                    ? "Admin\n" + (it.banned_by_name || "không rõ ai ban")
                    : "Spam trap";
                setTextCell(row, sourceText, "log-message");
                const channelText = it.channel_name
                    ? `#${it.channel_name}\n${it.channel_id || ""}`
                    : it.channel_id || "-";
                setTextCell(row, channelText, "log-message");
                const reason = it.reason_text || it.audit_reason || "-";
                const msg = (it.message_content || "").trim();
                setTextCell(row, msg ? `${reason}\n→ ${msg}` : reason, "log-message");
                body.appendChild(row);
            });
        } catch {
            body.innerHTML = '<tr><td colspan="5" class="readonly-empty">Không tải được ban log.</td></tr>';
        }
    }

    /* ── Tickets ──────────────────────────────────────────── */

    async function loadTickets() {
        const body = document.getElementById("ticketsTableBody");
        const total = document.getElementById("ticketsTotal");
        if (!body) return;
        try {
            const res = await fetch("/api/tickets/transcripts");
            const data = await res.json();
            const items = data.items || [];
            if (total) {
                total.textContent = items.length ? `${items.length} ticket đã đóng` : "";
            }
            body.innerHTML = "";
            if (!items.length) {
                body.innerHTML = '<tr><td colspan="6" class="readonly-empty">Chưa có ticket nào đã đóng.</td></tr>';
                return;
            }
            items.forEach((it) => {
                const row = document.createElement("tr");
                const num = String(it.ticket_number ?? "?").padStart(4, "0");
                setTextCell(row, "#" + num);
                const user = (it.user_name || "-") + (it.user_id ? `\n${it.user_id}` : "");
                setTextCell(row, user, "log-message");
                setTextCell(row, it.opened_at || "-");
                setTextCell(row, it.closed_at || "-");
                const closedBy = (it.closed_by_name || "-") + (it.closed_by ? `\n${it.closed_by}` : "");
                setTextCell(row, closedBy, "log-message");
                const td = document.createElement("td");
                if (it.filename) {
                    const a = document.createElement("a");
                    a.href = "/api/tickets/transcripts/" + encodeURIComponent(it.filename);
                    a.textContent = "Tải .txt";
                    a.className = "btn ghost";
                    a.setAttribute("download", it.filename);
                    td.appendChild(a);
                } else {
                    td.textContent = "-";
                }
                row.appendChild(td);
                body.appendChild(row);
            });
        } catch {
            body.innerHTML = '<tr><td colspan="6" class="readonly-empty">Không tải được transcripts.</td></tr>';
        }
    }

    async function downloadAllTranscripts() {
        try {
            const res = await fetch("/api/tickets/transcripts/download_all");
            if (!res.ok) {
                const data = await res.json().catch(() => null);
                const msg = (data && data.message) || `Không tải được (HTTP ${res.status}).`;
                showToast(msg, "warning");
                return;
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
            a.href = url;
            a.download = `transcripts-${ts}.zip`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            showToast("Đã tải toàn bộ transcript zip.", "success");
        } catch (err) {
            showToast("Lỗi tải zip: " + (err.message || err), "error");
        }
    }

    async function downloadBanLog() {
        try {
            const res = await fetch("/api/ban_log/download");
            if (!res.ok) {
                const data = await res.json().catch(() => null);
                const msg = (data && data.message) || `Không tải được (HTTP ${res.status}).`;
                showToast(msg, "warning");
                return;
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "ban_log.jsonl";
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            showToast("Đã tải ban_log.jsonl", "success");
        } catch (err) {
            showToast("Lỗi khi tải file: " + (err.message || err), "error");
        }
    }

    /* ── Version ──────────────────────────────────────────── */

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value || "-";
    }

    async function loadVersion() {
        try {
            const res = await fetch("/api/version");
            const info = await res.json();
            setText("versionBranch", info.branch);
            setText("versionCommit", info.commit);
            setText("versionDirty", info.dirty ? "Có thay đổi local" : "Sạch");
            setText("versionPython", info.python);
            setText("versionSubject", info.commit_subject);
            setText("versionTime", info.commit_time);
            setText("versionBind", `${info.dashboard_host || "-"}:${info.dashboard_port || "-"}`);
            setText("versionPublicUrl", info.public_url || "Chưa cấu hình");
            setText("versionFullCommit", info.full_commit);
            setText("versionCheckedAt", info.checked_at);
        } catch {
            setText("versionSubject", "Không tải được thông tin version.");
        }
    }

    /* ── Settings form ────────────────────────────────────── */

    function splitIds(value) {
        return String(value || "").split(",").map((s) => s.trim()).filter(Boolean);
    }

    function renderReadOnlyDisplays() {
        document.querySelectorAll("[data-display-for]").forEach((box) => {
            const fieldId = box.dataset.displayFor;
            const field = document.getElementById(fieldId);
            const ids = splitIds(field ? field.value : "");
            renderChips(box, ids);
        });
        renderSteamAppDisplays();
    }

    function renderChips(box, ids) {
        box.innerHTML = "";
        if (!ids.length) {
            const empty = document.createElement("span");
            empty.className = "readonly-empty";
            empty.textContent = "Chưa cấu hình trong .env";
            box.appendChild(empty);
            return;
        }
        ids.forEach((id) => {
            const chip = document.createElement("span");
            chip.className = "readonly-chip";
            chip.textContent = channelMap[id] || "ID: " + id;
            box.appendChild(chip);
        });
    }

    function parseSteamAppEntries(value) {
        return splitIds(value)
            .map((item) => {
                const m = item.match(/^(\d+)(?:[_:\-|]\s*(.+))?$/);
                if (!m) return null;
                return { id: m[1], name: (m[2] || "Steam App " + m[1]).trim() };
            })
            .filter(Boolean);
    }

    function renderSteamAppDisplays() {
        document.querySelectorAll("[data-steam-app-display]").forEach((box) => {
            const fieldId = box.dataset.steamAppDisplay;
            const field = document.getElementById(fieldId);
            const entries = parseSteamAppEntries(field ? field.value : "");
            box.innerHTML = "";
            if (!entries.length) {
                const empty = document.createElement("span");
                empty.className = "readonly-empty";
                empty.textContent = "Chưa có game. Dùng /game add <app_id> trên Discord.";
                box.appendChild(empty);
                return;
            }
            entries.forEach((entry, idx) => {
                const chip = document.createElement("span");
                chip.className = "readonly-chip";
                chip.textContent = `${idx + 1}. ${entry.id} — ${entry.name}`;
                box.appendChild(chip);
            });
        });
    }

    /* ── Multi-select picker (role/channel) ───────────────── */

    const multiPickers = [];

    function initMultiPickers() {
        document.querySelectorAll("[data-picker-for]").forEach((root) => {
            if (root.dataset.pickerInited === "true") return;
            root.dataset.pickerInited = "true";

            const hidden = root.querySelector('input[type="hidden"]');
            const chipsBox = root.querySelector("[data-picker-chips]");
            const input = root.querySelector("[data-picker-input]");
            const suggest = root.querySelector("[data-picker-suggest]");
            const prefix = root.dataset.pickerPrefix || "";
            const single = root.dataset.pickerSingle === "true";
            // Optional virtual entries (vd "@everyone", "@here") — format "id1:label1,id2:label2"
            const extras = (root.dataset.pickerExtras || "")
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean)
                .map((s) => {
                    const [id, ...rest] = s.split(":");
                    return [id.trim(), rest.join(":").trim() || id.trim()];
                });
            if (!hidden || !chipsBox || !input || !suggest) return;

            function getSelected() {
                return splitIds(hidden.value);
            }

            function labelFor(id) {
                const extra = extras.find(([eid]) => eid === id);
                if (extra) return extra[1];
                return channelMap[id] || id;
            }

            function setSelected(ids) {
                if (single && ids.length > 1) ids = ids.slice(-1);
                hidden.value = ids.join(",");
                render();
            }

            function render() {
                const ids = getSelected();
                chipsBox.innerHTML = "";
                ids.forEach((id) => {
                    const chip = document.createElement("span");
                    chip.className = "multi-picker-chip";
                    const label = document.createElement("span");
                    label.textContent = labelFor(id);
                    chip.appendChild(label);
                    const x = document.createElement("button");
                    x.type = "button";
                    x.className = "multi-picker-chip-x";
                    x.textContent = "×";
                    x.title = "Bỏ chọn";
                    x.addEventListener("click", () => {
                        setSelected(getSelected().filter((i) => i !== id));
                    });
                    chip.appendChild(x);
                    chipsBox.appendChild(chip);
                });
            }

            function buildPool() {
                const fromMap = Object.entries(channelMap)
                    .filter(([_id, label]) => !prefix || label.startsWith(prefix))
                    .sort((a, b) => a[1].localeCompare(b[1]));
                return extras.concat(fromMap);
            }

            function refreshSuggest(query) {
                const selected = new Set(getSelected());
                const q = (query || "").trim().toLowerCase();
                const matches = buildPool()
                    .filter(([id, label]) => {
                        if (selected.has(id)) return false;
                        if (!q) return true;
                        return label.toLowerCase().includes(q) || id.includes(q);
                    })
                    .slice(0, 60);

                suggest.innerHTML = "";
                if (!matches.length) {
                    const empty = document.createElement("div");
                    empty.className = "multi-picker-suggest-empty";
                    empty.textContent = q ? "Không có kết quả khớp" : "Không còn lựa chọn";
                    suggest.appendChild(empty);
                } else {
                    matches.forEach(([id, label]) => {
                        const item = document.createElement("button");
                        item.type = "button";
                        item.className = "multi-picker-suggest-item";
                        item.textContent = label;
                        item.addEventListener("mousedown", (e) => {
                            e.preventDefault();
                            if (single) {
                                setSelected([id]);
                            } else {
                                const ids = getSelected();
                                if (!ids.includes(id)) ids.push(id);
                                setSelected(ids);
                            }
                            input.value = "";
                            if (single) {
                                suggest.classList.remove("show");
                                input.blur();
                            } else {
                                refreshSuggest("");
                            }
                        });
                        suggest.appendChild(item);
                    });
                }
                suggest.classList.add("show");
            }

            input.addEventListener("focus", () => refreshSuggest(input.value));
            input.addEventListener("input", () => refreshSuggest(input.value));
            input.addEventListener("blur", () => {
                setTimeout(() => suggest.classList.remove("show"), 150);
            });
            input.addEventListener("keydown", (e) => {
                if (e.key === "Escape") {
                    suggest.classList.remove("show");
                    input.blur();
                } else if (e.key === "Backspace" && !input.value) {
                    const ids = getSelected();
                    if (ids.length) {
                        ids.pop();
                        setSelected(ids);
                    }
                }
            });

            multiPickers.push({ render });
            render();
        });
    }

    function refreshMultiPickers() {
        multiPickers.forEach((p) => p.render());
    }

    function updateHints() {
        document.querySelectorAll("[data-hint-for]").forEach((hint) => {
            const id = hint.dataset.hintFor;
            const el = document.getElementById(id);
            if (!el) return;
            const update = () => {
                const names = splitIds(el.value).map((v) => channelMap[v]).filter(Boolean);
                hint.textContent = names.length ? names.join(", ") : "";
            };
            el.oninput = update;
            el.onchange = update;
            update();
        });
    }

    // .env cũ dùng SPAM_TRAP_CHANNEL_ID + _2; gộp vào ô picker mới nếu ô mới còn trống.
    function migrateLegacySpamTrapChannels(config) {
        const field = document.getElementById("SPAM_TRAP_CHANNEL_IDS");
        if (!field || field.value.trim()) return;
        const ids = ["SPAM_TRAP_CHANNEL_ID", "SPAM_TRAP_CHANNEL_ID_2"]
            .flatMap((key) => splitIds(config[key]))
            .filter((id, i, arr) => arr.indexOf(id) === i);
        field.value = ids.join(",");
    }

    async function loadSettings() {
        await loadChannels();
        try {
            const res = await fetch("/api/config");
            const config = await res.json();
            lastConfig = config;
            for (const [key, value] of Object.entries(config)) {
                const el = document.getElementById(key);
                if (!el) continue;
                el.value = value || "";
            }
            migrateLegacySpamTrapChannels(config);
            renderReadOnlyDisplays();
            updateHints();
            initMultiPickers();
            refreshMultiPickers();
        } catch {
            showToast("Không tải được cấu hình.", "error");
        }
    }

    async function saveSettings() {
        const form = document.getElementById("settingsForm");
        if (!form) return;
        const data = {};
        form.querySelectorAll("input").forEach((input) => {
            if (!input.name) return;
            const allowEmpty = input.dataset.allowEmpty === "true";
            data[input.name] = input.type === "hidden" && !input.value && !allowEmpty && lastConfig[input.name]
                ? lastConfig[input.name]
                : input.value;
        });
        form.querySelectorAll("select:not([multiple])").forEach((sel) => {
            if (sel.name) data[sel.name] = sel.value;
        });
        form.querySelectorAll("textarea").forEach((ta) => {
            if (ta.name) data[ta.name] = ta.value;
        });
        // Steam form (separate <form> on a different page)
        const steamForm = document.getElementById("steamForm");
        if (steamForm) {
            steamForm.querySelectorAll("input").forEach((input) => {
                if (!input.name) return;
                data[input.name] = input.type === "hidden" && !input.value && lastConfig[input.name]
                    ? lastConfig[input.name]
                    : input.value;
            });
            steamForm.querySelectorAll("select:not([multiple])").forEach((sel) => {
                if (sel.name) data[sel.name] = sel.value;
            });
        }

        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await res.json();
            showToast(result.message, result.success ? "success" : "warning", "Cấu hình");
            setTimeout(fetchStatus, 1500);
        } catch {
            showToast("Không lưu được cấu hình.", "error");
        }
    }

    /* ── Bind global handlers ────────────────────────────── */

    function bindActions() {
        if (els.btnStart) els.btnStart.addEventListener("click", startBot);
        if (els.btnStop) els.btnStop.addEventListener("click", stopBot);

        document.querySelectorAll("[data-action]").forEach((btn) => {
            const action = btn.dataset.action;
            btn.addEventListener("click", () => {
                if (action === "refresh-channels") sendRefreshChannels();
                else if (action === "steamdb-check") sendSteamDBCheck();
                else if (action === "save-settings") saveSettings();
                else if (action === "reload-settings") loadSettings();
                else if (action === "reload-version") loadVersion();
                else if (action === "reload-logs") loadLogs();
                else if (action === "reload-banlog") loadBanLog();
                else if (action === "recount-ban-counter") sendRecountBanCounter();
                else if (action === "download-banlog") downloadBanLog();
                else if (action === "reload-tickets") loadTickets();
                else if (action === "download-all-transcripts") downloadAllTranscripts();
                else if (action === "open-env") openEnvModal();
                else if (action === "close-modal") closeModal(btn.closest(".modal-backdrop"));
            });
        });

        document.querySelectorAll(".modal-backdrop").forEach((bd) => {
            bd.addEventListener("click", (e) => {
                if (e.target === bd) closeModal(bd);
            });
        });
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                document.querySelectorAll(".modal-backdrop.show").forEach(closeModal);
            }
        });

    }

    /* ── Boot ─────────────────────────────────────────────── */

    document.addEventListener("DOMContentLoaded", async () => {
        bindNav();
        bindSettingsTabs();
        bindActions();
        activatePage("dashboard");
        await loadSettings();
        await loadVersion();
        await loadLogs();
        fetchStatus();
        fetchMetrics();
        setInterval(fetchStatus, 3000);
        setInterval(fetchMetrics, 2000);
        setInterval(loadLogs, 10000);
        setInterval(updateUtc7NowDisplay, 30000);
        window.addEventListener("resize", () => {
            renderSpark(els.cpuSparkline, cpuBuffer, Math.max(100, lastCpuCount * 100));
            renderSpark(els.ramSparkline, ramBuffer);
        });
    });

    // expose for debug
    window.__dashboard = { activatePage, fetchStatus, fetchMetrics, showToast };
})();
