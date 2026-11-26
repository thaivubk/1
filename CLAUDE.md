# Văn phòng Agent Kế toán

Bộ agent Claude Code làm các việc kế toán lặp lại (soát hồ sơ thanh toán, quyết toán, công đoàn, văn bản mới) kèm dashboard theo dõi chạy trên laptop.
Thiết kế: `docs/superpowers/specs/2026-11-24-van-phong-agent-ke-toan-design.md`.

## Working preferences

- Gọi người dùng là "đại ca"; không dùng "anh/chị" hay "bạn".
- Trả lời và viết giao diện, tin nhắn, file kết quả bằng tiếng Việt.
- Không commit dữ liệu hồ sơ, sổ cái, kết quả hay khóa bí mật vào repo.

## Khi nhận lệnh qua Telegram hoặc chat

Phiên Claude Code mở với kênh Telegram chỉ làm việc nhận lệnh, không tự soát hồ sơ trong phiên này.

- Tin nhắn có đường dẫn thư mục công việc: chạy `python -m vpak.giao_viec "<thư mục>"` (thêm `--loai tt|qt|qd|cd` nếu đại ca nói rõ loại việc, `--ghi-chu "..."` nếu có ghi chú).
- Đại ca hỏi "có gì cần quyết": chạy `python -m vpak.giao_viec --cau-hoi`.
- Đại ca trả lời một câu hỏi: chạy `python -m vpak.giao_viec --tra-loi <mã câu hỏi> "<câu trả lời>"`.
- Trả lời Telegram đúng một câu ngắn, dựa vào dòng kết quả lệnh in ra.
