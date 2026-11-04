# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- Chủ bot (admin, người vận hành VPS) và vài staff của Cánh Cụt Team (nhóm Việt hoá game). Staff không nhất thiết rành kỹ thuật.
- Tình huống: mở nhanh để bật/tắt bot, kiểm tra bot còn sống không, sửa cấu hình `.env`, xem log sự kiện / ban log, tải transcript ticket, tải video TikTok/Douyin không logo.
- Dùng trên máy tính và điện thoại ngang nhau; điện thoại thường để thao tác nhanh (bật/tắt, xem log).

## Product Purpose

Dashboard web (Flask, một trang, JS thuần) điều khiển một bot Discord moderation chạy trên VPS: spam trap (ban ai chat vào kênh bẫy), auto-delete theo từ khoá, auto role, ticket system, Steam patch watcher, tải TikTok/Douyin. Thành công = thấy ngay trạng thái bot, thao tác điều khiển/cấu hình không nhầm, đọc log nhanh, trên cả hai thiết bị.

## Operating Context

- Server Discord của Cánh Cụt Team; bot và dashboard chạy cùng máy (VPS Linux, hoặc Windows khi dev), dashboard bind localhost/public URL.
- Dashboard poll `/api/status` và `/api/metrics` mỗi 3 giây; lệnh gửi cho bot qua IPC file; "Lưu cấu hình" ghi `.env` và restart bot.
- Nội dung chủ yếu là tiếng Việt, xen ID Discord dài (18–19 chữ số), tên kênh `#kênh`, role, timestamp UTC+7.

## Capabilities and Constraints

- Trang: Tổng quan (status, PID, kênh cache, uptime, sparkline CPU/RAM, tác vụ nhanh), Cấu hình (5 tab: Cơ bản, Spam trap, Auto role, Ticket, Kênh log), Steam Watcher, Tải TikTok, Log gần đây, Ban log, Tickets (transcript), Version (git + ổ đĩa).
- Kỹ thuật: `templates/index.html` + `static/dashboard.css` + `static/dashboard.js` (vanilla, không build step). JS bám vào id/`data-*`/class hiện có; mọi id, `data-action`, `data-page`, `data-settings-*`, `data-picker-*`, `data-display-for`, `data-hint-for`, và các class JS sinh ra (`toast`, `status-pill online/offline/disconnected`, `sidebar-footer`, `log-level <level>`, `readonly-chip/empty`, `multi-picker-*`, `tt-*`, `kv-row`, `spark .line/.area`, `btn ghost/success`) phải giữ nguyên.
- Font tải từ Google Fonts; không có bundler, không framework CSS.
- Nhiều dữ liệu dạng bảng dài (log 100 dòng, ban log, transcript) cần cuộn ngang trên mobile.

## Brand Commitments

- Giữ nền tối.
- Giữ "cảm giác Discord": blurple `#5865F2`, hệ màu trạng thái xanh/đỏ/vàng kiểu Discord, bố cục sidebar + nội dung.
- Tên hiển thị: "Bot Dashboard" / "Discord moderator"; chủ server là Cánh Cụt Team (không có logo/màu riêng được cung cấp).

## Evidence on Hand

- Mã nguồn dashboard hiện tại (theme Discord tối) tại `templates/index.html`, `static/dashboard.css`, `static/dashboard.js`.
- Không có logo hay bộ màu riêng của Cánh Cụt Team; không bịa thêm.

## Product Principles

1. Trạng thái bot và nút bật/tắt luôn thấy ngay, ở mọi trang, mọi kích thước màn hình.
2. Hành động nguy hiểm (tắt bot, lưu & restart) phải phân biệt rõ với hành động thường.
3. Dữ liệu kỹ thuật (ID, PID, timestamp, commit) hiển thị bằng font đơn cách, dễ chọn/copy.
4. Điện thoại là công dân hạng nhất: điều hướng với tới bằng ngón cái, bảng cuộn được, không vỡ bố cục.
5. Staff không rành kỹ thuật vẫn hiểu nhãn và thông báo; không dùng thuật ngữ nội bộ nếu có từ phổ thông.
