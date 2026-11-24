# Văn phòng Agent Kế toán — Bản thiết kế

Ngày: 24/11/2026 · Trạng thái: chờ người dùng duyệt
Bản mẫu giao diện (dữ liệu minh họa): https://claude.ai/artifact/7Df1MsHVLLPhFieepkLvvA

## 1. Mục đích và lý do

Người dùng (gọi là "đại ca") là kế toán viên Ban Kế toán tài chính, phụ trách phân tích hồ sơ thanh toán, quyết toán dự án vốn đầu tư XDCB, mua sắm tập trung, KHCN, và chuyển đổi số của Ban. Phần lớn thời gian đi vào các việc lặp lại: liệt kê hồ sơ, soát logic giữa các văn bản, soát các lỗi hay gặp, điền mẫu tờ trình / báo cáo, cập nhật báo cáo thu chi công đoàn.

Đại ca muốn **một agent chủ nhận lệnh, tự chia việc cho các agent chuyên môn**, và **nhìn thấy được hết** các agent đang làm gì, đến đâu, trên một dashboard dễ theo dõi. Kênh ra lệnh (Telegram hay chat Claude) không quan trọng bằng việc **thấy được tiến độ**.

Thành công nghĩa là: đại ca trỏ vào một thư mục hồ sơ đang làm dở, bấm giao việc, đi làm việc khác; quay lại thấy trên dashboard (và nhận tin Telegram) danh mục hồ sơ, các lỗi đã phát hiện kèm nguồn (file nào, trang nào), các câu hỏi cần đại ca quyết, và file kết quả đã điền theo mẫu.

## 2. Mục tiêu, không làm, và điều tuyệt đối tránh

**Mục tiêu**
- Một agent Giao việc nhận lệnh (từ dashboard, Telegram hoặc cửa sổ Claude Code), tự chia việc cho các agent theo "phòng".
- Dashboard trên laptop cho thấy toàn bộ việc giao qua lại giữa các agent dưới dạng **sổ cái**, trạng thái, tiến độ, phát hiện, câu hỏi chờ quyết, kết quả.
- Soát hồ sơ thanh toán / quyết toán theo 3 cấp: đủ hồ sơ, logic văn bản, lỗi hay gặp (theo trí nhớ).
- Trí nhớ hồ sơ (lỗi hay gặp, sếp hay xem, mới học) lớn dần theo các lần đại ca sửa hoặc quyết.
- Điền mẫu có sẵn trong thư mục công việc; thiếu mẫu thì hỏi.
- Công đoàn: đọc file Excel sổ cái xuất từ phần mềm, nhặt thu / chi vào báo cáo thu chi.
- Đọc văn bản mới, tóm tắt điểm thay đổi so với quy trình hiện hành.
- Hiện danh sách việc cần làm lấy từ Google Sheet "Quản lý công việc" (chỉ đọc).
- Báo Telegram khi xong việc, có lỗi, hoặc cần đại ca quyết.

**Không làm (v1)**
- Không đưa dashboard lên Internet; chỉ chạy trên laptop. Điện thoại dùng Telegram.
- Không làm phần mã công việc / điểm thư viện / chấm điểm đánh giá (sheet 01_TVCV, 02_DGCV-CN).
- Không nhập / sửa việc cần làm từ dashboard; nhập, nhắc, đánh giá việc vẫn qua bot Telegram + Apps Script + Gemini hiện có của đại ca, không thay đổi luồng đó.
- Không dùng nhiều người; chỉ một người dùng.

**Điều tuyệt đối tránh (chạy được vẫn coi là hỏng)**
- Agent **sửa, xóa, ghi đè** bất kỳ file gốc nào trong thư mục hồ sơ. Agent chỉ được ghi vào thư mục con kết quả (mục 6.4).
- Agent **tự kết luận "hồ sơ đạt"** hoặc tự quyết điểm nghiệp vụ còn mơ hồ thay vì hỏi.
- Phát hiện **không có nguồn** (không nói file nào, trang / dòng nào) — đại ca không kiểm lại được thì vô dụng.
- Dữ liệu hồ sơ, sổ cái, kết quả, khóa bí mật bị **đẩy lên GitHub** hoặc gửi ra ngoài.
- Phát sinh chi phí API riêng: hệ thống phải chạy bằng gói Claude của công ty mà đại ca đang dùng.

## 3. Ràng buộc

- Laptop cơ quan chạy Windows, đã cài Python và được cài thêm thư viện; Claude Code đăng nhập bằng tài khoản Claude công ty (gói Team/Enterprise, chưa xác nhận).
- Kênh Telegram của Claude Code (plugin channel) đã kết nối. Kênh là tính năng thử nghiệm; với gói Team/Enterprise phải được quản trị bật (đại ca đã dùng được, coi như đã bật).
- Agent SDK của Anthropic bắt buộc API key trả tiền theo lượng dùng → không dùng.
- Thư mục công việc rất nhiều; mỗi lần giao việc chỉ làm trong **một** thư mục.
- Ngôn ngữ giao diện, tin nhắn, file kết quả: tiếng Việt.
- Hồ sơ có PDF scan, Word, Excel; bộ quyết toán có thể tới vài chục đến trăm file → phải tiết kiệm token.

## 4. Các hướng đã cân nhắc

| Hướng | Mô tả | Được | Mất | Kết luận |
|---|---|---|---|---|
| **A. Claude Code + dashboard Python trên laptop** | Agent là file hướng dẫn `.claude/agents/*.md`; Claude Code chạy agent (tương tác qua Telegram, hoặc chạy nền `claude -p` cho từng việc); hook tự ghi sổ cái; server Python nhỏ phục vụ dashboard | Dùng gói Claude công ty, không tốn API; ít mã; sửa hướng dẫn agent bằng chữ; tận dụng kênh Telegram đã có; agent con giao tiếp được cho agent cháu (tối đa 3 tầng), chạy song song | Laptop phải bật; tiến độ theo bước, không mượt; kênh Telegram là tính năng thử nghiệm | **Chọn** |
| B. Chương trình riêng bằng Claude Agent SDK + web + bot riêng | Tự viết điều phối bằng Python | Kiểm soát hoàn toàn, chạy như dịch vụ | Bắt buộc API key trả tiền theo token (chính sách Anthropic), không dùng được gói công ty; nhiều mã phải bảo trì | Bỏ |
| C. n8n / công cụ kéo-thả | Luồng tự động gọi Claude API | Ít mã | Cũng cần API key; giao diện theo dõi kém; khó đọc file trên laptop | Bỏ |

Đại ca chọn hướng A.

## 5. Tổng quan kiến trúc

```
 Dashboard (trình duyệt, http://127.0.0.1:8765)          Telegram
        │  giao việc / trả lời câu hỏi                      │ lệnh, trả lời
        ▼                                                    ▼
 Server Python (dashboard/) ── khởi chạy ──► claude -p (mỗi việc một tiến trình)
        │  đọc                                 Claude Code phiên tương tác (kênh Telegram)
        ▼                                                    │
   Sổ cái (JSONL)  ◄──── hook SubagentStart/Stop ────────────┤
        ▲          ◄──── tools/ghi_so.py (agent gọi) ────────┤
        │                                                    ▼
   Trí nhớ, danh mục chuẩn (.md)  ◄── agent đọc / ghi ── Agent Giao việc
                                                       ├─ phòng Thanh toán / Quyết toán / Soát xét / Quy trình–Quy định / Công đoàn
                                                       └─ Agent Tổng hợp → thư mục kết quả + Telegram
 Google Sheet "Quản lý công việc" ──(Apps Script web app chỉ đọc)──► Server Python → khung Nhớ việc
```

Hai đường vào cùng một bộ agent:
1. **Từ dashboard:** server chạy `claude -p` cho từng việc (chạy nền, song song có giới hạn).
2. **Từ Telegram / cửa sổ Claude Code:** phiên Claude Code tương tác (mở với kênh Telegram) đóng vai Giao việc.

Cả hai ghi vào **cùng một sổ cái**, nên dashboard thấy hết bất kể việc giao từ đâu.

## 6. Thành phần chi tiết

### 6.1 Kho mã và dữ liệu

- **Kho mã (repo này)**, clone về laptop (ví dụ `D:\VanPhongAgent`): hướng dẫn agent, hook, công cụ Python, dashboard, danh mục hồ sơ chuẩn, trí nhớ (chỉ quy tắc chung, không số hợp đồng / tên người), CLAUDE.md.
- **Thư mục dữ liệu ngoài repo** (ví dụ `D:\VanPhongAgent_data`, cấu hình được): sổ cái, nhật ký từng việc, ảnh chụp trạng thái token, file `.env` chứa khóa bí mật. `.gitignore` phải chặn mọi thứ này.
- Không bao giờ commit nội dung hồ sơ. Builder kiểm tra repo GitHub đang để private.

### 6.2 Danh sách agent (theo phòng, mỗi phòng một màu trên dashboard)

| Phòng (màu) | Agent | Việc |
|---|---|---|
| Điều phối (xanh navy) | **Giao việc** | Nhận lệnh, xem nhanh thư mục (đếm file, loại file, có mẫu không), tạo mã việc, ghi sổ, lập kế hoạch theo loại việc, giao cho agent phòng, gom câu hỏi |
| Thanh toán (xanh ngọc) | Liệt kê hồ sơ | Liệt kê file trong thư mục, đối chiếu **danh mục hồ sơ chuẩn**, chỉ ra hồ sơ thiếu |
| | Đối chiếu hợp đồng | Đối chiếu giá trị đề nghị, lũy kế, tạm ứng với điều khoản thanh toán của hợp đồng |
| Quyết toán (tím) | Tổng hợp giá trị | Tổng hợp giá trị đề nghị quyết toán theo hạng mục |
| | Đối chiếu số liệu | Khớp số đã thanh toán với số liệu kế toán có trong thư mục |
| Soát xét (hồng sẫm) | Cấp 1 · Đủ hồ sơ | Đủ chứng từ, đúng mẫu, đủ chữ ký / đóng dấu |
| | Cấp 2 · Logic văn bản | Số tiền bằng số – bằng chữ; số tiền, ngày tháng, tên đơn vị, MST, số hợp đồng, số hiệu văn bản khớp nhau giữa tờ trình, biên bản, hóa đơn, hợp đồng, bảo lãnh; thứ tự ngày hợp lý |
| | Cấp 3 · Lỗi hay gặp | Soát theo **trí nhớ**: từng mục "lỗi hay gặp" và "sếp hay xem" |
| Quy trình – Quy định (nâu) | Theo dõi văn bản mới | Đọc văn bản mới, tóm tắt điểm thay đổi so với quy trình hiện hành |
| | Kiểm chứng viện dẫn | Kiểm tra số hiệu, điều khoản, hiệu lực văn bản được viện dẫn trong hồ sơ |
| Công đoàn (xanh ô liu) | Đọc sổ cái | Đọc file Excel sổ cái, lấy các dòng thu / chi trong kỳ |
| | Cập nhật báo cáo | Ghi tiếp thu / chi vào báo cáo thu chi |
| Tổng hợp (xám đá) | **Tổng hợp** | Gom kết quả, điền mẫu (tờ trình, báo cáo thẩm tra quyết toán, báo cáo…) có trong thư mục, lập phiếu soát xét, lưu thư mục kết quả, báo Telegram |

Màu phòng tránh trùng màu trạng thái (xanh dương = đang làm, xanh lá = xong, cam = chờ đại ca, đỏ = phát hiện). Mã màu cụ thể lấy theo bản mẫu.

Ghi chú: tài khoản Claude của đại ca có sẵn skill `soat-xet-ho-so-thanh-toan` và `kiem-chung-van-ban`; nếu dùng được trong Claude Code trên laptop thì agent tương ứng nên tận dụng.

### 6.3 Kế hoạch mẫu theo loại việc

Giao việc chọn kế hoạch theo loại việc (đoán từ thư mục, đại ca đổi được trên form). Mũi tên là "chờ việc trước xong".

- **Soát thanh toán:** Giao việc → (Liệt kê hồ sơ ∥ Kiểm chứng viện dẫn) → Liệt kê xong thì (Đối chiếu hợp đồng ∥ Cấp 1 ∥ Cấp 2) → Cấp 2 xong thì Cấp 3 → tất cả xong thì Tổng hợp (điền mẫu thanh toán, phiếu soát xét, danh mục hồ sơ thiếu).
- **Soát quyết toán:** Giao việc → (Liệt kê hồ sơ ∥ Đối chiếu số liệu) → Tổng hợp giá trị → Cấp 2 → Cấp 3 → Tổng hợp (điền mẫu báo cáo thẩm tra quyết toán…).
- **Văn bản, quy trình:** Giao việc → Theo dõi văn bản mới → Kiểm chứng viện dẫn → Tổng hợp (bản tóm tắt + đề xuất cập nhật quy trình / trí nhớ).
- **Công đoàn:** Giao việc → Đọc sổ cái → Cập nhật báo cáo → Tổng hợp.
- **Lập báo cáo** (tự do): Giao việc tự lập kế hoạch.

Agent con được giao tiếp cho agent cháu nếu cần (Claude Code cho phép tối đa 3 tầng); giới hạn số agent chạy cùng lúc để tiết kiệm token (builder chọn mức, mặc định thấp).

### 6.4 Một việc từ đầu đến cuối

1. **Đầu vào:** đường dẫn một thư mục công việc + loại việc + ghi chú (không bắt buộc). Từ dashboard: dán đường dẫn, bấm "Duyệt…" (mở hộp chọn thư mục của Windows phía server), hoặc chọn trong danh sách **thư mục đang làm dở gần đây** (các thư mục đã giao việc trước đó, kèm trạng thái dừng ở đâu). Từ Telegram: nhắn lệnh có đường dẫn.
2. **Xem nhanh:** Giao việc đếm file theo loại, tìm file mẫu trong thư mục (tờ trình, báo cáo thẩm tra quyết toán, mẫu báo cáo, file báo cáo công đoàn), báo trước khi chạy.
3. **Mẫu:** có mẫu trong thư mục → dùng. Không có → **dừng hỏi** đại ca: dùng mẫu gần nhất cùng loại (từ việc trước) hay đại ca chỉ mẫu khác. Danh mục hồ sơ chuẩn (thanh toán / quyết toán) là cố định, lưu trong repo, không cần tìm trong thư mục.
4. **Chạy:** giao việc theo kế hoạch mẫu; mọi lần giao / bắt đầu / tiến độ / phát hiện / câu hỏi / xong đều vào sổ cái.
5. **Câu hỏi cần quyết:** agent ghi câu hỏi (kèm 2 lựa chọn gợi ý) vào sổ cái và báo Telegram; **việc khác không bị chặn**. Đại ca trả lời trên dashboard hoặc Telegram. Câu trả lời được ghi vào sổ cái và vào "Mới học" của trí nhớ (nếu là quy tắc dùng lại được).
6. **Kết quả:** Tổng hợp lưu vào **thư mục con `KetQua_Agent\<ngày>_<mã việc>\`** nằm ngay trong thư mục công việc (giữ kết quả cạnh hồ sơ). Đây là nơi duy nhất agent được ghi. File gốc không bị đụng tới; với báo cáo công đoàn, ghi ra **bản mới** trong thư mục kết quả chứ không sửa file gốc.
7. **Báo:** Telegram nhắn tóm tắt (số phát hiện, câu hỏi còn treo, đường dẫn thư mục kết quả). Dashboard có nút mở thư mục kết quả bằng Explorer.

Mã việc: `HS-` (thanh toán / quyết toán), `VB-` (văn bản), `CD-` (công đoàn), `BC-` (báo cáo) + số tăng dần.

### 6.5 Sổ cái

- File JSONL chỉ ghi thêm, mỗi tháng một file, trong thư mục dữ liệu. Mỗi dòng là một sự kiện: `job_created`, `task_assigned`, `task_started`, `progress`, `finding`, `question`, `decision`, `task_done`, `job_done`, `error`, `notify`.
- Trường chung: thời điểm, mã việc, mã công việc con, agent giao, agent nhận, nội dung; `finding` có thêm `nguon` (file + trang / dòng) và `nhan` (Lỗi hay gặp / Sếp hay xem nếu khớp trí nhớ).
- **Hai đường ghi:**
  - Hook `SubagentStart` / `SubagentStop` của Claude Code tự ghi khi agent bắt đầu / kết thúc (có `agent_type`, `agent_id`, `session_id`) — để sổ không phụ thuộc việc agent "nhớ" ghi.
  - Công cụ `tools/ghi_so.py` mà agent gọi để ghi giao việc, tiến độ, phát hiện, câu hỏi, kết quả (hook không mang nội dung phát hiện).
- Cách nối sự kiện của hook với mã việc / mã công việc con (ví dụ qua `session_id`, `agent_id`, hoặc yêu cầu agent ghi `agent_id` khi bắt đầu) để builder thiết kế; tài liệu Claude Code không ghi rõ hook có mang mô tả công việc hay không.
- Tiến độ % = theo bước: agent tự báo "đã soát 12/23 file" qua `ghi_so.py`; mức hồ sơ = trung bình các việc con.

### 6.6 Dashboard

Server Python chỉ lắng nghe `127.0.0.1` (cổng mặc định 8765), phục vụ một trang web, cập nhật gần thời gian thực (thăm dò vài giây hoặc SSE — builder chọn). Bố cục theo bản mẫu:

1. **Trên cùng:** thanh **Token 5 giờ** và **Token tuần** (mục 6.9), trạng thái Claude Code / Telegram.
2. Tiêu đề, 4 ô chỉ số: việc đang chạy, chờ đại ca quyết, việc đã xong, phát hiện cần xử lý.
3. **Ô giao việc:** (1) thư mục công việc: dán đường dẫn / Duyệt / chọn thư mục đang làm dở gần đây, kèm "xem nhanh" (số file, có mẫu chưa, sẽ soát theo trí nhớ nào); (2) loại việc tự chọn sẵn, đổi được; (3) ghi chú; dòng "Lệnh sẽ gửi" xem trước.
4. **Cột trái — sơ đồ văn phòng:** Giao việc ở trên, các phòng ở giữa (mỗi phòng một màu), Tổng hợp ở dưới kèm hộp kết quả và tin đã nhắn Telegram. Mỗi agent có hình nhân vật, trạng thái (đang làm / rảnh / chờ đại ca), việc hiện tại, thanh tiến độ. Bấm agent → lọc sổ cái theo agent.
5. **Cột phải:** khung **Cần đại ca quyết** (nút trả lời); khung **Nhớ việc** (mục 6.8); **Sổ cái công việc** kiểu sổ kế toán (cột Chứng từ, Diễn giải, Giao → Nhận, Trạng thái, Tiến độ, Phát hiện, Kết quả; gom theo hồ sơ; lọc theo phòng; bấm dòng mở nhật ký, phát hiện kèm nguồn, file kết quả; dòng "Cộng phát sinh"); khung **Trí nhớ hồ sơ** (Lỗi hay gặp, Sếp hay xem, Mới học).
6. Xưng hô trên giao diện và tin nhắn: "đại ca".

Server khởi chạy việc bằng `claude -p` với: thư mục làm việc là repo, quyền truy cập thêm thư mục hồ sơ, quyền ghi giới hạn vào `KetQua_Agent`, danh sách công cụ được phép tối thiểu, chế độ quyền không cần bấm duyệt tay. Không đặt `ANTHROPIC_API_KEY` (để dùng gói đăng nhập); không dùng `--bare`. Giới hạn số việc chạy song song (mặc định 2). Câu trả lời của đại ca cho một việc chạy nền được đưa lại bằng cách tiếp tục phiên (`--resume`) hoặc cơ chế tương đương — builder chọn, miễn đáp ứng mục 6.4 bước 5.

### 6.7 Telegram

- **Nhận lệnh:** qua kênh Telegram của Claude Code đã kết nối, vào phiên Claude Code tương tác (đóng vai Giao việc). Phiên này phải đang mở trên laptop.
- **Gửi thông báo** (xong, lỗi, cần quyết) cho cả việc chạy nền: dùng một công cụ Python gửi tin qua Telegram Bot API (token trong `.env`), vì việc chạy `claude -p` không có kênh. Dùng cùng bot với kênh hay bot riêng: builder chọn sau khi kiểm tra plugin trên máy.
- Trả lời câu hỏi qua Telegram phải ghi được vào sổ cái như trả lời trên dashboard.
- Bot quản lý công việc (Apps Script + Gemini) của đại ca là **bot khác**, giữ nguyên.

### 6.8 Nhớ việc (chỉ đọc từ Google Sheet)

- Nguồn: Google Sheet "Quản lý công việc", sheet **VIEC_CAN_LAM** (cột: ID, Nội dung công việc, Ngày giao, Hạn hoàn thành, Trạng thái, Kết quả/Sản phẩm).
- Cách lấy: một **Apps Script web app mới, độc lập** (không sửa script hiện có), `doGet` trả JSON các dòng VIEC_CAN_LAM, yêu cầu khóa bí mật trong tham số; server Python lấy định kỳ (ví dụ 5 phút) và khi bấm làm mới. Không xuất bản sheet công khai.
- Hiển thị: Quá hạn / Hôm nay / Sắp tới / Đã xong theo Hạn hoàn thành và Trạng thái. **Đánh dấu dòng nghi sai hạn** (hạn trước ngày giao). Nút "Giao cho agent" chép nội dung việc sang ô giao việc.
- Không ghi gì vào Sheet. Nhập, nhắc, đánh giá việc vẫn qua Telegram như cũ.

### 6.9 Thanh token 5 giờ / tuần

- Claude Code đưa `rate_limits.five_hour` / `rate_limits.seven_day` (`used_percentage`, `resets_at`) vào đầu vào của **status line**. Một script status line ghi các số này ra file trong thư mục dữ liệu; dashboard đọc file đó.
- Tài liệu chỉ cam kết các trường này cho gói Pro / Max / Ultra; gói Team / Enterprise **chưa rõ**. Builder kiểm tra trên laptop. Nếu không có: dashboard ghi "Gói hiện tại không cung cấp số liệu" và hiện mức sử dụng theo từng việc (lấy từ kết quả JSON của `claude -p`) thay thế.

### 6.10 Trí nhớ hồ sơ

- File Markdown trong repo: `tri-nho/loi-hay-gap.md`, `tri-nho/sep-hay-xem.md`, `tri-nho/moi-hoc.md`. Mỗi mục một dòng, có số lần gặp / ngày học.
- Agent Cấp 3 soát từng mục. Khi phát hiện khớp một mục → gắn nhãn và tăng đếm.
- Khi đại ca quyết hoặc sửa kết quả → thêm vào `moi-hoc.md` (ngày, mã việc, quy tắc). Định kỳ đại ca (hoặc agent theo lệnh) chuyển mục "mới học" đã ổn định sang hai file chính.
- **Nạp ban đầu:** lỗi hay gặp nằm rải rác trong các chat Claude cũ của đại ca. Đại ca dán danh sách sang (hoặc đưa file xuất dữ liệu claude.ai); builder chuẩn hóa thành các file trên. Ví dụ đã biết: bảo lãnh thiếu ngày (phát hành / hiệu lực / hết hạn); người ký bảo lãnh không đúng ủy quyền của ngân hàng; bảo lãnh thiếu tiền so với tỷ lệ trong hợp đồng; biên bản nghiệm thu không đúng quy định bài đo; biên bản thiếu chữ ký giám sát / tư vấn; số tiền bằng chữ không khớp bằng số.
- Không ghi số hợp đồng, tên người, số tiền cụ thể vào trí nhớ (chỉ quy tắc chung), vì các file này nằm trong repo.

### 6.11 Đọc file và tiết kiệm token

- Ưu tiên trích chữ bằng Python (PDF có lớp chữ, Word, Excel) rồi mới đưa cho agent; chỉ đọc ảnh trang (PDF scan) khi cần.
- Agent liệt kê / đọc sổ cái có thể dùng model rẻ hơn; agent soát logic dùng model mạnh. Builder chọn cụ thể.

## 7. Bảo mật

- Server chỉ nghe `127.0.0.1`; không mở ra mạng.
- Khóa bí mật (token bot, khóa Apps Script web app) trong `.env` ngoài repo.
- Quyền ghi của agent giới hạn vào `KetQua_Agent` và thư mục dữ liệu; cấm xóa file.
- Sheet CAU_HINH của đại ca đang để Gemini API key và token bot Telegram dạng chữ thường; đã khuyến nghị đại ca chuyển sang Script Properties và đổi khóa. Hệ thống mới không đọc sheet CAU_HINH.

## 8. Thứ tự làm đề xuất

1. Nền: repo, thư mục dữ liệu, sổ cái + `ghi_so.py` + hook, dashboard đọc sổ cái (sơ đồ văn phòng, sổ cái, câu hỏi).
2. Luồng **Soát thanh toán** chạy trọn từ dashboard, có câu hỏi / trả lời, kết quả, báo Telegram.
3. Nhận lệnh qua Telegram vào cùng luồng.
4. Trí nhớ hồ sơ (nạp ban đầu + học thêm).
5. Soát quyết toán; Công đoàn; Văn bản, quy trình.
6. Nhớ việc (Google Sheet); thanh token.

Thử nghiệm bằng một bộ hồ sơ mẫu đã xóa thông tin nhạy cảm do đại ca cung cấp.

## 9. Đầu vào cần đại ca cung cấp khi làm

- Danh mục hồ sơ chuẩn thanh toán và quyết toán (hoặc cho phép lấy từ skill `soat-xet-ho-so-thanh-toan`).
- Danh sách lỗi hay gặp / sếp hay xem từ các chat cũ.
- Một bộ hồ sơ thanh toán mẫu (đã xóa thông tin nhạy cảm) để thử.
- Cặp file mẫu công đoàn: sổ cái Excel xuất từ phần mềm + báo cáo thu chi.
- Quy trình hiện hành của Ban (file) để agent văn bản so sánh.
- Triển khai Apps Script web app chỉ đọc (builder viết mã, đại ca dán và triển khai).

## 10. Các điểm Claude tự chốt (đại ca xem lại)

- **Danh mục hồ sơ chuẩn:** một danh mục cố định cho thanh toán, một cho quyết toán (đại ca xác nhận các dự án đều giống nhau), chia theo giai đoạn (tạm ứng, thanh toán từng đợt, đợt cuối / quyết toán). Điều khoản thanh toán của hợp đồng nếu đòi thêm hồ sơ thì **cộng thêm** vào danh mục; vì vậy Liệt kê hồ sơ đọc điều khoản thanh toán của hợp đồng trước.
- **Giới hạn dùng gói:** mặc định chạy song song 2 việc; nếu có số liệu token và mức 5 giờ vượt 80% thì tạm giữ việc mới trong hàng chờ và báo đại ca. Đại ca nên hỏi quản trị xem tài khoản có bật "dùng vượt hạn mức có tính phí" không.
- **Cài đặt trên laptop:** builder không có quyền vào laptop, nên kế hoạch phải kèm một script kiểm tra môi trường (Claude Code, Python, kênh Telegram, số liệu token, skill có sẵn, chính sách quyền) và hướng dẫn cài từng bước để đại ca chạy; mọi chỗ "kiểm tra trên laptop" phải có phương án dự phòng bật / tắt trong cấu hình.
- **PDF scan:** mặc định để Claude đọc trang dạng ảnh khi không trích được chữ; OCR cục bộ (Tesseract tiếng Việt) là tùy chọn làm sau nếu tốn token.
- **Skill có sẵn** (`soat-xet-ho-so-thanh-toan`, `kiem-chung-van-ban`): chỉ dùng phần kiến thức (danh mục, cách tra cứu); không dùng nguyên các bước ghi đè file gốc hoặc tự kết luận "đạt" vì trái mục 2.

## 11. Câu hỏi còn mở (chờ đại ca)

1. Agent có được **đọc** thư mục cha / các thư mục đợt trước (hợp đồng gốc, lũy kế, tạm ứng) không? Với file **cộng dồn** (list hồ sơ thanh – quyết toán theo hợp đồng, báo cáo thu chi công đoàn cả năm), agent ghi bản mới vào thư mục kết quả hay được cập nhật thẳng file gốc sau khi sao lưu và hỏi xác nhận?
2. Mẫu để trong thư mục là **mẫu trống** hay **file đợt trước đã điền** (cần thay số liệu)? Phiếu soát xét / phiếu đánh giá hồ sơ có mẫu cố định không?
3. Dữ liệu được ra ngoài laptop đến đâu: tin Telegram có được ghi nội dung phát hiện ngắn (tên chứng từ, số tiền) không; agent kiểm chứng có được tra web công khai (vbpl.vn, thuvienphapluat) bằng số hiệu văn bản không?

## 12. Để builder quyết

Cấu trúc thư mục cụ thể, thư viện Python, cách cập nhật thời gian thực, định dạng chi tiết sự kiện sổ cái, cách nối hook với mã việc, cơ chế tiếp tục việc sau câu trả lời, model cho từng agent, giới hạn song song, cách mở hộp chọn thư mục, tên file kết quả.
