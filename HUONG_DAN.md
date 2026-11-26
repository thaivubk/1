# Hướng dẫn cài và dùng Văn phòng Agent Kế toán

Dành cho đại ca, làm trên laptop cơ quan (Windows). Làm lần lượt từ trên xuống.

## 1. Lấy mã về máy (một lần)

1. Mở PowerShell, chuyển tới ổ muốn đặt công cụ, ví dụ `cd D:\`.
2. Chạy `git clone https://github.com/thaivubk/1 VanPhongAgent` rồi `cd VanPhongAgent`.
3. Chuyển sang nhánh có mã: `git checkout claude/accounting-multi-agent-tool-d0jrp7`.

## 2. Cài đặt (một lần)

1. Chạy `powershell -ExecutionPolicy Bypass -File scripts\cai_dat.ps1`.
2. Script tạo môi trường Python riêng, cài thư viện, tạo file `.env`, rồi in bảng kiểm tra máy.
3. Mở `.env` bằng Notepad và điền:
   - `TELEGRAM_BOT_TOKEN`: token bot Telegram dùng để báo kết quả.
   - `TELEGRAM_CHAT_ID`: mã cuộc trò chuyện của đại ca với bot.
   - `VPAK_LOOKUP_URL`: link web app tra cứu văn bản của đại ca (cả phần `?key=...`).
4. Chạy lại `.venv\Scripts\python.exe -m vpak.kiem_tra --gui-thu`. Mọi mục bắt buộc phải có dấu ✔, và Telegram nhận được tin "Văn phòng Agent đã kết nối."

File `.env` chứa khóa bí mật, không gửi cho ai và không đưa lên GitHub (đã được chặn sẵn).

## 3. Mỗi ngày làm việc

1. Mở dashboard: `powershell -ExecutionPolicy Bypass -File scripts\chay.ps1`. Trình duyệt tự mở `http://127.0.0.1:8765`. Giữ cửa sổ PowerShell này mở trong lúc làm việc.
2. Muốn ra lệnh qua Telegram: mở thêm một cửa sổ PowerShell, chạy `powershell -ExecutionPolicy Bypass -File scripts\telegram.ps1`.

## 4. Giao việc

- Trên dashboard: dán đường dẫn thư mục đang làm dở (hoặc bấm "Duyệt…", hoặc bấm một thư mục gần đây), rồi bấm **Giao việc**.
- Qua Telegram: nhắn đường dẫn thư mục, ví dụ "Soát hồ sơ D:\CongViec\2026\HD-125\Dot4".
- Agent chỉ đọc hồ sơ. Kết quả nằm trong thư mục con `KetQua_Agent` của chính thư mục đó.
- Mẫu list hồ sơ, mẫu báo cáo thẩm tra quyết toán, mẫu báo cáo: đại ca để sẵn trong thư mục cần làm. Agent tạo file mới giống mẫu, không sửa file mẫu.

## 5. Khi agent hỏi

- Khung **Cần đại ca quyết** trên dashboard hiện câu hỏi và các nút trả lời.
- Hoặc nhắn Telegram "có gì cần quyết", rồi trả lời theo mã câu hỏi.
- Quyết định nào dùng lại được sẽ được ghi vào `tri-nho/moi-hoc.md`.

## 6. Sửa trí nhớ và danh mục

- `tri-nho/loi-hay-gap.md`, `tri-nho/sep-hay-xem.md`: mỗi dòng bắt đầu bằng `- ` là một mục agent sẽ soát.
- `danh-muc/ho-so-thanh-toan.md`: danh mục hồ sơ chuẩn theo giai đoạn. Đây là bản nháp, đại ca sửa lại cho đúng danh mục của Ban.

## 7. Khi có lỗi

- Dashboard báo "Mất kết nối với máy chủ": cửa sổ chạy `chay.ps1` đã bị đóng, mở lại.
- Việc báo lỗi "Không tìm thấy Claude Code trên máy": chạy `claude --version` trong PowerShell để kiểm tra Claude Code đã cài và đăng nhập chưa.
- Chạy `.venv\Scripts\python.exe -m vpak.kiem_tra` để xem bảng kiểm tra máy.
