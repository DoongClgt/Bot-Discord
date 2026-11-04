---
version: 1
slug: "templates-index-html"
primary_target: "templates/index.html"
related_targets: ["static/dashboard.css","static/dashboard.js"]
---

# Surface: dashboard (templates/index.html + static/dashboard.css + static/dashboard.js)

Mode: Operate. Platform: web. Build path: code-led.

Audience: chủ bot + vài staff Cánh Cụt Team; mở trên máy tính và điện thoại ngang nhau. Việc: thấy bot sống/chết, bật/tắt, sửa .env, đọc log/ban log, tải transcript, tải TikTok.

Pinned by brief: nền tối, blurple #5865F2, bố cục sidebar + nội dung, JS hooks giữ nguyên.

## Direction contract

THESIS: Dashboard đọc như một sổ patch notes đang được duy trì của một dịch vụ đang chạy: mỗi màn là một ledger có dấu thời gian, có phiên bản, kẻ bằng hairline, chứ không phải lưới thẻ giống nhau. Từ chối: lưới metric-card bo tròn + sparkline tile rời rạc, mỗi thứ một hộp.

OWN-WORLD: Nền tối ngả blurple (ink #14151b, panel #1b1d25, raised #22252f, hairline #2b2e3a), chữ #eef0f6 / muted #9aa0b4. Blurple là accent duy nhất: mục đang chọn, nút chính, focus ring, vạch chọn bên trái. Màu trạng thái chỉ cho trạng thái: online #3ba55d, offline/danger #ed4245, warn #f0b232, info/link #58a6ff. Chữ UI: Be Vietnam Pro (có glyph tiếng Việt chuẩn); dữ liệu, ID, PID, timestamp, commit, số liệu: JetBrains Mono. Ngôn ngữ thành phần: hàng ledger kẻ hairline thay vì hộp; tiêu đề mục kiểu "release heading" có stamp mono bên phải (số đếm, thời điểm cập nhật); tag mức log như tag patch [info][warn][error] dạng mono pill viền trái; trạng thái = chấm + chữ mono. Mật độ: hàng 36–40px, bảng cột mono, padding 20px desktop / 14px mobile.

STORY: Staff mở lên, dòng đầu tiên đọc như header một bản phát hành: "Online · uptime 3d 4h · PID 1234 · 87 kênh". Bên dưới là dòng sự kiện gần nhất. Nút Bật/Tắt luôn ở đầu. Cấu hình là ledger key → giá trị theo tab; log/ban log/ticket là ledger dài cuộn ngang được trên mobile.

FIRST VIEWPORT (desktop 1366): rail trái 232px: brand, nav 8 mục có vạch blurple trái khi active, footer trạng thái. Main: thanh đầu dính (sticky) 60px: tên trang + mô tả | chip trạng thái mono + PID + Bật/Tắt. Tổng quan: một "dòng phát hành" kẻ hairline chia 4 cột (Trạng thái, Uptime, PID, Kênh cache) số mono 26px, không hộp; tiếp theo hai dải CPU/RAM: nhãn + giá trị mono + sparkline nền trong, cùng một panel chia đôi bằng hairline; rồi hàng Tác vụ nhanh; rồi ledger "Sự kiện gần đây" (8 dòng cuối từ /api/logs) với cột thời gian mono, tag mức, nội dung. Mobile 390: header dính có brand + chip trạng thái + Bật/Tắt; rail nav thành dải chip cuộn ngang dính dưới header; 4 cột phát hành thành 2×2; bảng cuộn ngang.

FORM: Sổ patch notes / changelog ledger, vị trí 1 trong danh sách 7 hướng (người dùng chọn "lựa chọn của tôi" thay vì hướng được xúc xắc chỉ định số 6, bảng điểm esports). seed:e170233eb3837d67. Chuyển động: 150–200ms, chỉ cho trạng thái (toast trượt vào, tab đổi, chip chọn).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Quyết định sau finish review (2026-11-05)
- Bảng log / sự kiện trên mobile dùng `.log-table.stacked` (xếp chồng: thời gian + mức + sự kiện một hàng, nội dung dòng dưới) thay vì cuộn ngang — chủ đích, vì staff không rành kỹ thuật đọc trên điện thoại. Ban log, ticket vẫn cuộn ngang.
- Trên mobile, chip trạng thái + Bật/Tắt là thanh cố định dưới đáy (tầm ngón cái) thay vì dính ở đầu; "luôn thấy" là điều hợp đồng cần, vị trí đáy tốt hơn cho điện thoại.
- Font vẫn tải từ Google Fonts (máy build không tải được file woff2 để self-host); việc self-host còn mở.
