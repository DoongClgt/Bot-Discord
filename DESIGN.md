---
name: Bot Dashboard
description: Dashboard điều khiển bot Discord của Cánh Cụt Team — "sổ patch notes" nền tối, ledger kẻ hairline, số liệu mono, blurple làm accent duy nhất.
colors:
  ink: "#14151b"
  panel: "#1b1d25"
  raised: "#22252f"
  raised-2: "#292c38"
  hair: "#2b2e3a"
  hair-strong: "#383c4b"
  text: "#eef0f6"
  text-2: "#b4b9cb"
  text-3: "#868c9f"
  text-4: "#828899"
  blurple: "#5865f2"
  blurple-strong: "#6b76f5"
  blurple-hover: "#4752c4"
  blurple-dim: "rgba(88, 101, 242, 0.14)"
  ok: "#3ba55d"
  ok-text: "#8fe3a8"
  ok-button: "#1f7d3f"
  danger: "#ed4245"
  danger-text: "#ffb3b4"
  warn: "#f0b232"
  warn-text: "#ffd889"
  info: "#58a6ff"
  info-text: "#a6cfff"
typography:
  page-title:
    fontFamily: "Be Vietnam Pro, Segoe UI, Roboto, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  section-title:
    fontFamily: "Be Vietnam Pro, Segoe UI, Roboto, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Be Vietnam Pro, Segoe UI, Roboto, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Be Vietnam Pro, Segoe UI, Roboto, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 500
    lineHeight: 1.4
  stat:
    fontFamily: "JetBrains Mono, Cascadia Code, Consolas, ui-monospace, monospace"
    fontSize: "26px"
    fontWeight: 500
    lineHeight: 1.15
  data:
    fontFamily: "JetBrains Mono, Cascadia Code, Consolas, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
  stamp:
    fontFamily: "JetBrains Mono, Cascadia Code, Consolas, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "0.01em"
  table-head:
    fontFamily: "JetBrains Mono, Cascadia Code, Consolas, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.06em"
rounded:
  sm: "4px"
  md: "6px"
  lg: "10px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "28px"
  "7": "40px"
  gutter-desktop: "28px"
  gutter-mobile: "16px"
  rail: "232px"
  topbar: "60px"
components:
  button-primary:
    backgroundColor: "{colors.blurple}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    height: "34px"
    padding: "0 14px"
  button-primary-hover:
    backgroundColor: "{colors.blurple-hover}"
  button-start:
    backgroundColor: "{colors.ok-button}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    height: "34px"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.danger-text}"
    rounded: "{rounded.md}"
    height: "34px"
  button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    height: "34px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-2}"
    rounded: "{rounded.md}"
    height: "30px"
    padding: "0 10px"
  input:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.text}"
    typography: "{typography.data}"
    rounded: "{rounded.md}"
    height: "36px"
    padding: "0 12px"
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.text-2}"
    rounded: "{rounded.md}"
    height: "36px"
    padding: "0 12px"
  nav-item-active:
    backgroundColor: "{colors.blurple-dim}"
    textColor: "{colors.text}"
  status-pill:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-2}"
    typography: "{typography.data}"
    rounded: "{rounded.md}"
    padding: "5px 10px"
  log-tag:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text-3}"
    typography: "{typography.data}"
    rounded: "0 4px 4px 0"
    padding: "1px 7px 1px 6px"
  toast:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "12px 16px"
---

# Bot Dashboard — DESIGN.md

## Overview

Dashboard vận hành (Operate) cho bot Discord moderation của Cánh Cụt Team, dùng trên máy tính và điện thoại ngang nhau. Ý tưởng chủ đạo: **sổ patch notes đang được duy trì** của một dịch vụ đang chạy. Mỗi màn hình là một ledger có dấu thời gian: tiêu đề mục kiểu "release heading" với stamp mono bên phải, các hàng kẻ bằng hairline, dữ liệu kỹ thuật (ID, PID, timestamp, commit, số liệu) bằng font mono. Không dùng lưới thẻ giống nhau; hộp chỉ xuất hiện khi thật sự nổi lên trên trang (toast, popover, modal).

Ràng buộc thương hiệu: nền tối, cảm giác Discord (blurple `#5865F2`, bố cục rail trái + nội dung), tiếng Việt là ngôn ngữ chính.

## Colors

- **Nền**: `ink` cho vùng nội dung và ô nhập; `panel` cho rail trái; `raised` cho nút phụ, chip, popover; `raised-2` cho hover của nút phụ.
- **Hairline**: `hair` cho mọi đường kẻ ledger (bảng, hàng form, tiêu đề mục, phân cách rail/topbar); `hair-strong` cho viền ô nhập, chip, nút ghost.
- **Chữ**: `text` (nội dung chính, số liệu), `text-2` (nhãn, nội dung bảng), `text-3` (mô tả, hint), `text-4` (stamp, placeholder, tiêu đề cột — đã đo ≥4.5:1 trên `ink`/`panel`).
- **Accent duy nhất**: `blurple` cho nút chính, mục nav đang chọn (tint `blurple-dim` + vạch trái 2px), tab đang chọn, focus ring, chip chọn, màu chọn văn bản, sparkline CPU. Hover nút chính là `blurple-hover` (đậm hơn, giữ tương phản chữ trắng).
- **Màu trạng thái chỉ cho trạng thái**: `ok` (online, nút Bật bot dùng `ok-button` tối hơn để chữ trắng đủ tương phản), `danger` (offline, Tắt bot — nút viền, không tô đặc), `warn` (mất kết nối, log warn), `info` (log info, link, sparkline RAM). Các biến `*-text` là phiên bản sáng để đặt chữ trên nền tối; nền tint dùng `color-mix` 9–14%.

## Typography

- **UI**: Be Vietnam Pro (có đầy đủ dấu tiếng Việt), 14px thân, nhãn 12.5–13px weight 500, tiêu đề trang 20px/600, tiêu đề mục 15px/600. Một họ chữ cho toàn bộ UI; phân cấp bằng cỡ và trọng lượng.
- **Dữ liệu**: JetBrains Mono cho mọi thứ có thể copy hoặc so sánh: ID Discord, PID, timestamp, commit, số liệu, stamp, tiêu đề cột bảng (12px, tracking 0.06em, chữ hoa), tag mức log, chip trạng thái, giá trị trong ô nhập. Không dùng mono làm "trang phục kỹ thuật" cho chữ thường.
- Số liệu lớn (`stat`) 26px mono weight 500; `font-variant-numeric: tabular-nums` toàn trang.
- Font tải từ Google Fonts với `display=swap`; nếu self-host được thì đặt woff2 trong `static/fonts/` và khai báo `@font-face`.

## Layout

- **Desktop (>860px)**: rail trái 232px dính (sticky) full chiều cao, topbar 60px dính với nền mờ (backdrop-filter), nội dung gutter 28px. Topbar: tiêu đề + mô tả trang bên trái; chip trạng thái mono, PID, Bật bot, Tắt bot bên phải.
- **Tổng quan**: "dòng phát hành" 4 cột chia bằng hairline dọc (Trạng thái, Uptime, PID, Kênh cache), rồi cặp CPU/RAM chia đôi bằng hairline, rồi Tác vụ nhanh, rồi ledger Sự kiện gần đây (8 dòng cuối).
- **Trang cấu hình** (`.kv-form`): mỗi trường là một hàng key → giá trị (nhãn 30% trái, control phải), kẻ hairline giữa các hàng; tab ngang có gạch chân blurple.
- **Mobile (≤860px)**: rail thành header (brand) + dải nav cuộn ngang dính trên cùng, có fade mép phải; chip trạng thái + Bật/Tắt thành thanh cố định dưới đáy (tầm ngón cái, có safe-area); dòng phát hành 2×2 (1 cột dưới 360px); hàng form xếp dọc; bảng log/sự kiện xếp chồng (`.log-table.stacked`: thời gian + mức + sự kiện một hàng, nội dung dòng dưới); bảng ban log/ticket cuộn ngang (min-width 640px).
- Thang khoảng cách 4px: 4/8/12/16/20/28/40. Khoảng cách trên tiêu đề mục (28px) lớn hơn dưới (12px).

## Elevation & Depth

- Mặt phẳng chính là phẳng, phân cấp bằng hairline và tông nền (`ink` → `panel` → `raised`).
- Bóng chỉ cho thứ nổi khỏi trang: toast, popover gợi ý, modal — `0 10px 30px rgba(0,0,0,.45), 0 2px 6px rgba(0,0,0,.35)`.
- Topbar desktop và thanh hành động mobile dùng nền mờ 86–92% + blur 10px để nội dung cuộn phía sau vẫn đọc được.
- Focus: viền 2px blurple + ring `rgba(88,101,242,.45)` 3px cho ô nhập; `:focus-visible` outline 2px blurple cho mọi control.

## Shapes

- Bo góc nhỏ: 4px (chip, tag, code), 6px (nút, ô nhập, nav item, pill), 10px (modal). Không bo tròn hoàn toàn (pill 999px) trừ chấm trạng thái.
- Tag mức log: vạch trái 2px màu trạng thái, bo góc chỉ bên phải — đọc như tag `[info]` trong patch notes.
- Ô chỉ-đọc rỗng: viền đứt nét `hair-strong`, nền trong; có dữ liệu: viền liền `hair`, nền `raised`.

## Components

- **Nút**: cao 34px, 13px/500. Chính (blurple), Bật bot (xanh tối), Tắt bot (viền đỏ, hover tint đỏ), phụ (raised + viền), ghost (30px, viền, dùng trong bảng và tiêu đề mục). Disabled: opacity .45. Mỗi trang chỉ một nút chính.
- **Nav item**: 36px, icon 16px; active: tint blurple + vạch trái 2px + icon blurple; mobile: chip 32px với gạch dưới blurple.
- **Chip trạng thái**: mono 12px, chấm 7px; online xanh, offline đỏ, mất kết nối vàng nhấp nháy 1.4s.
- **Ledger head** (`.ledger-head`, `.card-header`): tiêu đề 15px + stamp mono + nút ghost đẩy sang phải, kẻ hairline dưới.
- **Bảng** (`.log-table`): tiêu đề cột mono hoa, hàng 9px padding kẻ hairline, hover tint nhẹ; cột thời gian/ID dùng `.cell-mono`; nội dung dài `.log-message` mono 12px pre-wrap.
- **Form**: ô nhập nền `ink`, viền `hair-strong`, chữ mono 13px; select có mũi tên SVG tự vẽ; hint 12px `text-3`.
- **Multi-picker**: chip chọn tint blurple với nút × (hover tint đỏ); popover gợi ý nổi (`.show`), item hover tint blurple.
- **Toast**: góc dưới phải (desktop), trên thanh hành động (mobile); icon màu theo mức; trượt lên 8px khi hiện.
- **Modal .env**: nền mờ, hộp panel bo 10px, `.kv-row` key mono xám / value mono trắng kẻ hairline.
- **Sparkline**: SVG trong suốt, đường 1.5px màu accent, vùng dưới 12% opacity; CPU blurple, RAM info.

## Do's and Don'ts

- Do: kẻ hairline để nhóm; thêm stamp mono (số đếm, thời điểm) vào mọi tiêu đề mục có dữ liệu; đặt ID/timestamp bằng mono để copy được.
- Do: giữ chuyển động 150–200ms, chỉ cho thay đổi trạng thái; tôn trọng `prefers-reduced-motion`.
- Do: trên mobile, giữ Bật/Tắt trong thanh đáy cố định ở mọi trang.
- Don't: bọc nội dung trong card bo tròn có viền chỉ để "trông gọn"; không lồng card trong card.
- Don't: dùng màu trạng thái (xanh/đỏ/vàng) cho trang trí hay nút không liên quan trạng thái; không có hai nút chính blurple cạnh nhau.
- Don't: dùng mono cho chữ mô tả; không dùng emoji thay icon; không giảm chữ dưới 12px.
- Don't: đổi tên id / `data-*` trong HTML — JS bám vào chúng.
