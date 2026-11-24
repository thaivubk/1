# Văn phòng Agent Kế toán — Kế hoạch 1: Nền tảng + luồng Soát thanh toán

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chạy được trọn một việc "Soát hồ sơ thanh toán" trên laptop của đại ca: giao việc từ dashboard 3D hoặc Telegram → agent Giao việc chia cho các agent con → sổ cái ghi lại mọi bước → dashboard hiện trực tiếp → câu hỏi chờ đại ca quyết → kết quả lưu vào `KetQua_Agent` → báo Telegram ngắn gọn.

**Architecture:** Gói Python `vpak` gồm: sổ cái JSONL (chỉ ghi thêm), hàm gom sự kiện thành trạng thái, CLI `ghi_so` cho agent gọi, hook Claude Code tự ghi khi agent con bắt đầu / kết thúc, bộ chạy việc khởi động `claude -p` cho từng việc, bộ báo Telegram, server FastAPI chỉ nghe `127.0.0.1` phục vụ giao diện 3D (dựng từ bản mẫu) và API. Agent là các file `.claude/agents/*.md`; agent Giao việc là lời nhắc của phiên `claude -p`.

**Tech Stack:** Python ≥ 3.10, FastAPI + uvicorn, openpyxl, pdfplumber, python-docx, pytest (+ httpx cho TestClient, fpdf2 chỉ dùng trong test), Three.js r128 (bản `three.min.js` để sẵn trong repo), Claude Code CLI (đăng nhập gói công ty).

**Spec:** `docs/superpowers/specs/2026-11-24-van-phong-agent-ke-toan-design.md` (bản mẫu giao diện: `docs/mockup/van-phong-agent-3d.html`)

**Ngoài phạm vi kế hoạch này (Kế hoạch 2):** luồng Soát quyết toán, Công đoàn, Văn bản – quy trình; khung Nhớ việc đọc Google Sheet; thanh token từ status line; nạp trí nhớ từ các chat cũ. Giao diện vẫn hiện đủ 13 agent; agent chưa có luồng thì ở trạng thái "Rảnh".

## Global Constraints

- Python ≥ 3.10; chạy chính trên Windows 10/11, test chạy được cả Linux. Dùng `pathlib`, `subprocess` với danh sách tham số, **không** `shell=True`.
- Server chỉ nghe `127.0.0.1`, cổng mặc định `8765` (`VPAK_PORT`).
- Thư mục dữ liệu mặc định `Path.home() / "VanPhongAgent_data"`, đổi bằng `VPAK_DATA`. Không gì trong thư mục này được commit.
- Khóa bí mật chỉ nằm trong `.env` ở gốc repo (đã `.gitignore`): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `VPAK_LOOKUP_URL` (web app tra cứu văn bản, có sẵn `?key=...`).
- Agent **chỉ đọc** thư mục hồ sơ và mọi thư mục con; **chỉ ghi** vào `<thư mục công việc>/KetQua_Agent/<YYYY-MM-DD>_<mã việc>/`; cấm xóa file; không sửa file mẫu (tạo file mới giống mẫu).
- Không đặt `ANTHROPIC_API_KEY` khi chạy `claude -p`; không dùng `--bare`.
- Chạy song song tối đa 2 việc (`VPAK_MAX_PARALLEL`, mặc định `2`).
- Mã việc: tiền tố `HS` (thanh toán / quyết toán), `VB` (văn bản), `CD` (công đoàn), `BC` (báo cáo) + `-` + 4 chữ số tăng dần chung, ví dụ `HS-0001`.
- Sổ cái: `<data>/so-cai/YYYY-MM.jsonl`, mỗi dòng một sự kiện JSON UTF-8 (`ensure_ascii=False`).
- Mọi chữ hiện cho người dùng, tin Telegram, file kết quả: tiếng Việt, xưng "đại ca".
- Tin Telegram chỉ báo ngắn gọn kết quả, đúng 3 mẫu: `Xong {job}: {n} phát hiện, kết quả đã lưu.` · `{job} chờ đại ca quyết {k} câu.` · `{job} gặp lỗi: {ly_do}`.
- Phát hiện (`finding`) bắt buộc có `nguon` (file + trang / dòng); thiếu thì CLI từ chối.
- Agent không bao giờ tự kết luận "hồ sơ đạt".

## Review Focus

- **Đường dẫn có dấu tiếng Việt, dấu cách, rất dài** (ví dụ `D:\Công Việc\2026\HĐ 125 Nhà trạm\Đợt 4`): giao việc, liệt kê file và truyền vào `claude -p` phải chạy đúng → test ở Task 6 và Task 8.
- **Nhiều agent ghi sổ cái cùng lúc** và dòng cuối bị ghi dở khi máy tắt: không hỏng dòng nào, dòng dở bị bỏ qua khi đọc → test ở Task 2.
- **Claude CLI không có / chưa đăng nhập / hết hạn mức**: việc kết thúc với sự kiện `error` có lý do tiếng Việt, dashboard và Telegram báo lỗi, không treo "Đang làm" → test ở Task 6.
- **Thư mục đã có `KetQua_Agent` từ lần chạy trước**: không được liệt kê kết quả cũ như hồ sơ → test ở Task 8.
- **Server khởi động lại khi việc đang chạy**: việc mồ côi (tiến trình đã chết, chưa có `job_run_ended`) chuyển sang lỗi "mất kết nối", không treo mãi → test ở Task 6.

---

## Cấu trúc file

```
pyproject.toml                 # gói vpak, phụ thuộc, cấu hình pytest
.env.example                   # các khóa cần điền (không có giá trị thật)
.gitignore                     # .env, .venv, __pycache__, dữ liệu
CLAUDE.md                      # (sửa) thêm quy ước dự án + cách nhận lệnh Telegram
HUONG_DAN.md                   # hướng dẫn cài và dùng cho đại ca
.claude/settings.json          # hook SubagentStart/SubagentStop
.claude/agents/*.md            # 7 agent của luồng thanh toán
prompts/giao_viec.md           # lời nhắc agent Giao việc (khuôn có chỗ trống)
tri-nho/loi-hay-gap.md, tri-nho/sep-hay-xem.md, tri-nho/moi-hoc.md
danh-muc/ho-so-thanh-toan.md   # danh mục hồ sơ chuẩn
vpak/__init__.py
vpak/config.py                 # đọc cấu hình + .env
vpak/catalog.py                # danh sách phòng, agent (nguồn duy nhất cho UI + state)
vpak/ledger.py                 # ghi / đọc sổ cái
vpak/state.py                  # gom sự kiện → trạng thái cho dashboard
vpak/ghi_so.py                 # CLI agent gọi để ghi sổ
vpak/hook.py                   # hook Claude Code
vpak/telegram.py, vpak/notifier.py
vpak/runner.py                 # tạo việc, chạy claude -p, hàng chờ, trả lời câu hỏi
vpak/tools/__main__.py         # CLI công cụ cho agent: doc, liet-ke, list-ho-so, tao-tu-mau, tra-cuu
vpak/tools/doc_file.py, liet_ke.py, list_ho_so.py, tao_tu_mau.py, tra_cuu.py
vpak/server.py                 # FastAPI + chạy uvicorn
vpak/giao_viec.py              # CLI giao việc (dùng trong phiên Telegram)
vpak/kiem_tra.py               # kiểm tra môi trường trên laptop
vpak/web/index.html            # giao diện 3D dùng dữ liệu thật
vpak/web/vendor/three.min.js   # Three.js r128 (MIT)
scripts/cai_dat.ps1, scripts/chay.ps1
tests/...                      # một file test cho mỗi module
```

---

### Task 1: Khung dự án và cấu hình

**Files:**
- Create: `pyproject.toml`, `.env.example`, `.gitignore`, `vpak/__init__.py`, `vpak/config.py`, `vpak/catalog.py`
- Test: `tests/test_config.py`, `tests/test_catalog.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Config: repo_dir: Path; data_dir: Path; port: int; max_parallel: int; telegram_token: str; telegram_chat_id: str; lookup_url: str; claude_cmd: list[str]`
  - `load_config(env: Mapping[str, str] | None = None, repo_dir: Path | None = None) -> Config` — đọc `<repo>/.env` (dòng `KEY=VALUE`, bỏ dòng trống và `#`), biến môi trường ghi đè `.env`; tạo `data_dir` nếu chưa có. `claude_cmd` = `shlex.split(VPAK_CLAUDE_CMD)` nếu có, ngược lại `[shutil.which("claude") or "claude"]`.
  - `catalog.ROOMS: list[dict]` mỗi phần tử `{"id","name","short","color"}` với id `tt, qt, sx, dp, qd, cd` và màu `#0F766E, #6D28D9, #BE185D, #1F3A5F, #92400E, #4D7C0F`.
  - `catalog.AGENTS: dict[str, dict]` khóa là id kebab: `giao-viec, tong-hop, liet-ke-ho-so, doi-chieu-hop-dong, tong-hop-gia-tri, doi-chieu-so-lieu, soat-cap-1, soat-cap-2, soat-cap-3, van-ban-moi, tra-cuu-van-ban, doc-so-cai, bao-cao-thu-chi`; mỗi giá trị `{"name","tag","room","role","acc"}` lấy theo bản mẫu (`docs/mockup/van-phong-agent-3d.html`, biến `AG`).

- [ ] **Step 1: Viết test**

```python
def test_defaults(tmp_path):
    cfg = load_config(env={"VPAK_DATA": str(tmp_path / "d")}, repo_dir=tmp_path)
    assert cfg.port == 8765 and cfg.max_parallel == 2
    assert cfg.data_dir.is_dir()

def test_env_file_and_override(tmp_path):
    (tmp_path / ".env").write_text("TELEGRAM_CHAT_ID=111\n# chú thích\nVPAK_PORT=9000\n", encoding="utf-8")
    cfg = load_config(env={"VPAK_PORT": "9100", "VPAK_DATA": str(tmp_path / "d")}, repo_dir=tmp_path)
    assert cfg.telegram_chat_id == "111" and cfg.port == 9100

def test_catalog_consistent():
    room_ids = {r["id"] for r in ROOMS}
    assert len(AGENTS) == 13 and all(a["room"] in room_ids for a in AGENTS.values())
```

- [ ] **Step 2: Chạy test, thấy FAIL** — `pytest tests/test_config.py tests/test_catalog.py -v` → lỗi import.
- [ ] **Step 3: Viết `pyproject.toml`** (phụ thuộc: `fastapi`, `uvicorn`, `openpyxl`, `pdfplumber`, `python-docx`; nhóm dev: `pytest`, `httpx`, `fpdf2`), `.gitignore` (`.env`, `.venv/`, `__pycache__/`, `*.pyc`), `.env.example` (4 khóa ở Global Constraints, giá trị rỗng), rồi `config.py`, `catalog.py`.
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Khung dự án vpak: cấu hình và danh mục agent"`

---

### Task 2: Sổ cái

**Files:**
- Create: `vpak/ledger.py`
- Test: `tests/test_ledger.py`

**Interfaces:**
- Consumes: `Config.data_dir`
- Produces:
  - `EVENT_TYPES = {"job_created","job_started","task_assigned","task_started","progress","finding","question","decision","task_done","job_done","job_run_ended","error","agent_started","agent_stopped","notify"}`
  - `append_event(data_dir: Path, type: str, **fields) -> dict` — thêm `id` (uuid4 hex), `ts` (ISO giờ địa phương, đến giây), ghi một dòng vào `so-cai/YYYY-MM.jsonl` dưới khóa file `so-cai/.lock` (tạo bằng `os.open(..., O_CREAT|O_EXCL)`, thử lại mỗi 20 ms tới 5 s, xóa khóa cũ hơn 30 s). `type` ngoài `EVENT_TYPES` → `ValueError`.
  - `read_events(data_dir: Path, months: int = 2) -> list[dict]` — đọc tháng hiện tại và tháng trước theo thứ tự thời gian; bỏ qua dòng không parse được.

- [ ] **Step 1: Viết test**

```python
def test_roundtrip_unicode(tmp_path):
    append_event(tmp_path, "finding", job="HS-0001", text="Bảo lãnh thiếu ngày", nguon="BL.pdf, trang 1")
    ev = read_events(tmp_path)[-1]
    assert ev["text"] == "Bảo lãnh thiếu ngày" and ev["type"] == "finding" and "ts" in ev

def test_monthly_file(tmp_path):
    append_event(tmp_path, "job_created", job="HS-0001")
    assert list((tmp_path / "so-cai").glob("*.jsonl"))[0].name == datetime.now().strftime("%Y-%m") + ".jsonl"

def test_concurrent_processes(tmp_path):  # Review Focus: ghi đồng thời
    with multiprocessing.Pool(4) as p:
        p.map(_write_50, [tmp_path] * 4)   # mỗi tiến trình ghi 50 sự kiện
    assert len(read_events(tmp_path)) == 200

def test_torn_last_line_skipped(tmp_path):  # Review Focus: dòng ghi dở
    append_event(tmp_path, "job_created", job="HS-0001")
    f = next((tmp_path / "so-cai").glob("*.jsonl"))
    f.write_text(f.read_text(encoding="utf-8") + '{"type": "fin', encoding="utf-8")
    assert len(read_events(tmp_path)) == 1

def test_unknown_type(tmp_path):
    with pytest.raises(ValueError):
        append_event(tmp_path, "abc")
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `ledger.py`** theo Interfaces.
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Sổ cái JSONL có khóa ghi đồng thời"`

---

### Task 3: Gom sự kiện thành trạng thái dashboard

**Files:**
- Create: `vpak/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: sự kiện từ `read_events`, `catalog.AGENTS`, `catalog.ROOMS`
- Produces: `build_state(events: list[dict], now: datetime | None = None) -> dict` trả về:
  - `jobs`: `[{"id","title","folder","kind","status"("run"|"review"|"done"|"error"),"pct","created","tasks":[...]}]`, mới nhất trước.
  - mỗi task: `{"id","job","from","to","desc","status"("wait"|"run"|"review"|"done"),"pct","finds","issues":[{"x","ref","nhan"}],"log":[{"t","x"}],"file","time"}`.
  - `agents`: `{agent_id: {"st"("run"|"review"|"idle"),"task": task_id|None,"pct","done": int}}` cho đủ 13 agent; ưu tiên `run` > `review` > `idle`.
  - `questions`: `[{"id","job","task","agent","q","choices":[str,str]}]` các câu chưa có `decision`.
  - `feed`: 30 dòng mới nhất `{"t","c"(màu phòng),"x"}`; `kpis`: `{"run","review","done","finds"}`.
- Quy tắc: `task_assigned` → task `wait`; `task_started` → `run`; `progress{pct}` → cập nhật pct (0–100); `finding` → `finds += 1`, thêm issue; `question` → task `review`; `decision{question}` → task của câu hỏi về `run`; `task_done{file?}` → `done`, pct 100; `job_done` / `error` → trạng thái việc; job `review` nếu có task `review`.

- [ ] **Step 1: Viết test**

```python
def test_flow_states():
    ev = [E("job_created", job="HS-0001", title="Dot4", folder="D:/x", kind="tt"),
          E("task_assigned", job="HS-0001", task="HS-0001.1", agent="soat-cap-2", desc="Soát cấp 2"),
          E("task_started", job="HS-0001", task="HS-0001.1", agent="soat-cap-2"),
          E("progress", job="HS-0001", task="HS-0001.1", pct=40)]
    s = build_state(ev)
    assert s["agents"]["soat-cap-2"] == {"st": "run", "task": "HS-0001.1", "pct": 40, "done": 0}
    assert s["agents"]["doc-so-cai"]["st"] == "idle"

def test_question_then_decision():
    ev = BASE + [E("question", job="HS-0001", task="HS-0001.1", agent="soat-cap-2", qid="Q1", q="Chấp nhận bản scan?", choices=["Chấp nhận", "Yêu cầu bản gốc"])]
    s = build_state(ev)
    assert s["questions"][0]["id"] == "Q1" and s["jobs"][0]["status"] == "review"
    s2 = build_state(ev + [E("decision", job="HS-0001", qid="Q1", answer="Chấp nhận")])
    assert s2["questions"] == [] and s2["agents"]["soat-cap-2"]["st"] == "run"

def test_finding_counts_and_kpis():
    s = build_state(BASE + [E("finding", job="HS-0001", task="HS-0001.1", agent="soat-cap-2", text="Sai ngày", nguon="BB.pdf tr1")])
    assert s["kpis"]["finds"] == 1 and s["jobs"][0]["tasks"][0]["issues"][0]["ref"] == "BB.pdf tr1"
```
(`E(type, **f)` là hàm trợ giúp trong test tạo dict có `ts` tăng dần; `BASE` = 3 sự kiện đầu của `test_flow_states`.)

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `state.py`** — hàm thuần, không đọc file.
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Gom sự kiện sổ cái thành trạng thái dashboard"`

---

### Task 4: CLI `ghi_so` và hook Claude Code

**Files:**
- Create: `vpak/ghi_so.py`, `vpak/hook.py`, `.claude/settings.json`
- Test: `tests/test_ghi_so.py`, `tests/test_hook.py`

**Interfaces:**
- Consumes: `append_event`, `load_config`
- Produces:
  - `ghi_so.main(argv: list[str] | None = None) -> int` — lệnh con (tên tiếng Việt không dấu): `giao --task --agent --desc`, `bat-dau --task --agent`, `tien-do --task --pct [--ghi-chu]`, `phat-hien --task --agent --text --nguon [--nhan "Lỗi hay gặp"|"Sếp hay xem"]`, `hoi --task --agent --q --chon "A" --chon "B"` (in ra `qid`), `xong --task [--file]`, `loi --text`, `xong-viec`. `--job` mặc định lấy `VPAK_JOB_ID`; thiếu job → in lỗi tiếng Việt, trả `2`. `phat-hien` thiếu `--nguon` → trả `2`. Thành công in `Đã ghi: <type>` và trả `0`.
  - `hook.main(stdin_text: str | None = None) -> int` — đọc JSON hook (`hook_event_name`, `agent_type`, `agent_id`, `session_id`); `SubagentStart` → `agent_started`, `SubagentStop` → `agent_stopped`, kèm `job=VPAK_JOB_ID`. Mọi lỗi ghi vào `<data>/hook-errors.log`, **luôn trả `0`**.
  - `.claude/settings.json`: hook `SubagentStart` và `SubagentStop` (matcher `*`) chạy lệnh `python -m vpak.hook`.

- [ ] **Step 1: Viết test**

```python
def test_phat_hien_requires_nguon(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path)); monkeypatch.setenv("VPAK_JOB_ID", "HS-0001")
    assert ghi_so.main(["phat-hien", "--task", "HS-0001.1", "--agent", "soat-cap-2", "--text", "Sai ngày"]) == 2
    assert ghi_so.main(["phat-hien", "--task", "HS-0001.1", "--agent", "soat-cap-2", "--text", "Sai ngày", "--nguon", "BB.pdf tr1"]) == 0
    assert read_events(tmp_path)[-1]["nguon"] == "BB.pdf tr1"

def test_hoi_prints_qid(tmp_path, monkeypatch, capsys): ...   # main(["hoi", ...]) == 0, stdout chứa "Q", sự kiện question có choices 2 phần tử

def test_missing_job(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path)); monkeypatch.delenv("VPAK_JOB_ID", raising=False)
    assert ghi_so.main(["bat-dau", "--task", "x", "--agent", "soat-cap-1"]) == 2

def test_hook_start_stop(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path)); monkeypatch.setenv("VPAK_JOB_ID", "HS-0001")
    hook.main(json.dumps({"hook_event_name": "SubagentStart", "agent_type": "soat-cap-1", "agent_id": "a1", "session_id": "s1"}))
    assert read_events(tmp_path)[-1]["type"] == "agent_started"

def test_hook_bad_json_never_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    assert hook.main("{không phải json") == 0
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `ghi_so.py` (argparse), `hook.py`, `.claude/settings.json`.**
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "CLI ghi sổ cho agent và hook SubagentStart/Stop"`

---

### Task 5: Báo Telegram

**Files:**
- Create: `vpak/telegram.py`, `vpak/notifier.py`
- Test: `tests/test_notifier.py`

**Interfaces:**
- Consumes: `read_events`, `Config`
- Produces:
  - `telegram.send_message(cfg: Config, text: str) -> bool` — POST `https://api.telegram.org/bot<token>/sendMessage` (`chat_id`, `text`), `urllib`, timeout 10 s; thiếu token / chat id hoặc lỗi mạng → `False`, không ném lỗi.
  - `class Notifier: __init__(self, data_dir: Path, send: Callable[[str], bool])`; `poll(self) -> int` — xét sự kiện mới sau con trỏ lưu ở `<data>/notifier.json` (theo `id` sự kiện cuối đã xét); `job_done` → mẫu "Xong", đếm `finding` của việc; mỗi `job_run_ended` của việc còn câu hỏi mở → mẫu "chờ đại ca quyết {k} câu."; `error` → mẫu "gặp lỗi" (lý do cắt 120 ký tự). Ghi sự kiện `notify` sau mỗi tin gửi được. Trả số tin đã gửi. Lần chạy đầu tiên chỉ đặt con trỏ, không gửi lại lịch sử.

- [ ] **Step 1: Viết test**

```python
def test_done_message(tmp_path):
    sent = []; n = Notifier(tmp_path, lambda t: sent.append(t) or True); n.poll()
    append_event(tmp_path, "finding", job="HS-0001", task="t", agent="soat-cap-1", text="x", nguon="y")
    append_event(tmp_path, "job_done", job="HS-0001")
    assert n.poll() == 1 and sent == ["Xong HS-0001: 1 phát hiện, kết quả đã lưu."]

def test_waiting_message(tmp_path): ...  # question mở + job_run_ended → "HS-0001 chờ đại ca quyết 1 câu."
def test_no_resend_after_restart(tmp_path): ...  # Notifier mới trên cùng data_dir, poll() == 0
def test_send_message_without_token_returns_false(tmp_path): ...
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `telegram.py`, `notifier.py`.**
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Báo Telegram ngắn gọn theo sự kiện sổ cái"`

---

### Task 6: Bộ chạy việc (`claude -p`)

**Files:**
- Create: `vpak/runner.py`, `prompts/giao_viec.md` (khung, nội dung đầy đủ ở Task 9), `tests/fake_claude.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `Config`, `append_event`, `read_events`, `build_state`
- Produces:
  - `guess_kind(folder: Path) -> str` — `cd` nếu đường dẫn chứa `congdoan`/`công đoàn`; `qd` nếu chứa `vanban`/`văn bản`/`quy-trinh`; `qt` nếu một phần tên bắt đầu `QT` hoặc chứa `quyet`/`quyết`; ngược lại `tt` (không phân biệt hoa thường, so cả bản bỏ dấu).
  - `class JobRunner: __init__(self, cfg: Config)`
    - `submit(self, folder: str, kind: str | None = None, note: str = "") -> str` — thư mục không tồn tại → `ValueError("Không tìm thấy thư mục: ...")`; cấp mã việc qua `<data>/counter.json`; ghi `job_created{job,title(2 cấp thư mục cuối nối bằng " › "),folder,kind,note}`; xếp hàng; trả mã việc.
    - `pump(self) -> None` — khởi chạy việc trong hàng khi số việc đang chạy < `max_parallel`; kiểm tra tiến trình đã xong.
    - `answer(self, qid: str, answer: str) -> None` — ghi `decision{job,qid,answer}`; khi tiến trình của việc đã dừng, chạy tiếp bằng `--resume <session_id>` với lời nhắn `Đại ca trả lời câu {qid}: {answer}. Làm tiếp các việc đang chờ.`
    - `recover(self) -> int` — gọi khi server khởi động: việc có `job_started` nhưng không có `job_run_ended` và PID (lưu trong `<data>/jobs/<job>.pid`) không còn sống → ghi `error{reason:"Mất kết nối khi server khởi động lại"}`; trả số việc đã xử lý.
  - Lệnh chạy: `cfg.claude_cmd + ["-p", prompt, "--output-format", "json", "--add-dir", folder, "--allowedTools", ALLOWED]`, `cwd=cfg.repo_dir`, env sao chép môi trường **bỏ `ANTHROPIC_API_KEY`**, thêm `VPAK_JOB_ID`, `VPAK_DATA`. `ALLOWED` = `Read,Glob,Grep,Task,WebSearch,WebFetch,Bash(python -m vpak.ghi_so:*),Bash(python -m vpak.tools:*),Write(<folder>/KetQua_Agent/**),Edit(<folder>/KetQua_Agent/**)`. stdout lưu `<data>/jobs/<job>.json`; khi xong ghi `job_run_ended{job,exit_code,session_id,usage}`; exit ≠ 0 hoặc không chạy được lệnh → `error{reason}` với lý do tiếng Việt (`Không tìm thấy Claude Code trên máy`, `Claude Code báo lỗi: <dòng cuối stderr>`).
  - `tests/fake_claude.py`: script giả đọc `-p`, ghi vài sự kiện bằng `vpak.ghi_so`, in JSON `{"session_id":"fake-1","result":"ok"}`; biến `FAKE_FAIL=1` thì thoát mã 1 và in stderr `Credit balance is too low`.

- [ ] **Step 1: Viết test**

```python
def test_submit_unicode_path(tmp_path, cfg):  # Review Focus: đường dẫn tiếng Việt, dấu cách
    folder = tmp_path / "Công Việc" / "HĐ 125 Nhà trạm" / "Đợt 4"; folder.mkdir(parents=True)
    job = JobRunner(cfg).submit(str(folder))
    ev = [e for e in read_events(cfg.data_dir) if e["type"] == "job_created"][-1]
    assert job == "HS-0001" and ev["title"] == "HĐ 125 Nhà trạm › Đợt 4" and ev["kind"] == "tt"

def test_guess_kind():
    assert guess_kind(Path(r"D:\CongViec\CongDoan\2026\T11")) == "cd"
    assert guess_kind(Path(r"D:\CongViec\2026\QT_De-tai-KHCN")) == "qt"

def test_run_with_fake_claude(tmp_path, cfg_fake):
    r = JobRunner(cfg_fake); job = r.submit(str(make_folder(tmp_path))); wait_until(lambda: (r.pump(), done(cfg_fake, job))[1])
    ended = [e for e in read_events(cfg_fake.data_dir) if e["type"] == "job_run_ended"][-1]
    assert ended["session_id"] == "fake-1" and ended["exit_code"] == 0

def test_claude_missing(tmp_path, cfg):  # Review Focus: thiếu Claude
    r = JobRunner(replace(cfg, claude_cmd=["khong-co-lenh-nay"])); job = r.submit(str(make_folder(tmp_path))); r.pump()
    assert last_error(cfg, job) == "Không tìm thấy Claude Code trên máy"

def test_claude_fails(...): ...  # FAKE_FAIL=1 → error chứa "Credit balance is too low", job status "error" trong build_state
def test_max_parallel(...): ...  # 3 việc, max_parallel=2 → đúng 2 job_started trước khi việc đầu xong
def test_recover_orphan(...): ...  # Review Focus: job_started + pid không sống → recover() == 1, có error "Mất kết nối..."
def test_env_has_no_api_key(...): ...  # fake_claude ghi lại os.environ; ANTHROPIC_API_KEY không có, VPAK_JOB_ID đúng
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `runner.py` và `tests/fake_claude.py`** (fixture `cfg_fake` đặt `claude_cmd=[sys.executable, "tests/fake_claude.py"]`).
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Bộ chạy việc claude -p có hàng chờ, trả lời câu hỏi, phục hồi"`

---

### Task 7: Server API

**Files:**
- Create: `vpak/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `Config`, `JobRunner`, `Notifier`, `read_events`, `build_state`, `catalog`
- Produces:
  - `create_app(cfg: Config, runner: JobRunner, notifier: Notifier | None = None) -> FastAPI`
  - `GET /api/state` → `build_state(...)` + `"catalog": {"rooms": ROOMS, "agents": AGENTS}` + `"recent": [{"path","name","job","status"}]` (≤ 6 thư mục của các việc gần nhất, không trùng) + `"quota": null`.
  - `POST /api/jobs` body `{"folder": str, "kind": str|null, "note": str}` → `{"job": "HS-0001"}`; `ValueError` → 400 `{"detail": "<thông báo tiếng Việt>"}`.
  - `POST /api/questions/{qid}/answer` body `{"answer": str}` → 200 `{"ok": true}`; qid không còn mở → 404 `{"detail":"Câu hỏi đã được trả lời hoặc không tồn tại"}`.
  - `POST /api/browse` → mở hộp chọn thư mục bằng `tkinter.filedialog.askdirectory` (luồng riêng) → `{"path": str|null}`.
  - `POST /api/open` body `{"path": str}` → `os.startfile` (Windows) chỉ khi path nằm dưới một thư mục của việc đã giao; ngoài ra 403.
  - `GET /` → `vpak/web/index.html`; `/vendor/*` → file tĩnh.
  - Luồng nền mỗi 3 s: `runner.pump()` và `notifier.poll()`. `main()` (`python -m vpak.server`) chạy `runner.recover()` rồi uvicorn `host="127.0.0.1", port=cfg.port`.

- [ ] **Step 1: Viết test** (dùng `fastapi.testclient.TestClient`, runner thật với `cfg_fake`)

```python
def test_state_shape(client): r = client.get("/api/state"); assert r.status_code == 200 and len(r.json()["catalog"]["agents"]) == 13
def test_bad_folder(client): r = client.post("/api/jobs", json={"folder": "Z:/khong/co"}); assert r.status_code == 400 and "Không tìm thấy thư mục" in r.json()["detail"]
def test_answer_unknown(client): assert client.post("/api/questions/Q404/answer", json={"answer": "x"}).status_code == 404
def test_open_outside_jobs_forbidden(client, tmp_path): assert client.post("/api/open", json={"path": str(tmp_path)}).status_code == 403
def test_index_served(client): assert "Văn phòng Agent" in client.get("/").text
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `server.py`.**
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Server FastAPI cho dashboard (chỉ 127.0.0.1)"`

---

### Task 8: Công cụ đọc và lập file cho agent

**Files:**
- Create: `vpak/tools/__init__.py`, `vpak/tools/__main__.py`, `doc_file.py`, `liet_ke.py`, `list_ho_so.py`, `tao_tu_mau.py`, `tra_cuu.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `Config`
- Produces (và lệnh CLI tương ứng `python -m vpak.tools <lệnh>` in kết quả ra stdout, UTF-8):
  - `liet_ke.list_files(folder: Path) -> list[dict]` — đệ quy, **bỏ qua mọi thư mục tên `KetQua_Agent`**, mỗi phần tử `{"rel","ext","size","pages"(PDF)|None}`, sắp theo `rel`. CLI: `liet-ke <folder>` in bảng.
  - `doc_file.extract_text(path: Path, max_chars: int = 60000) -> str` — PDF (pdfplumber, đánh dấu `--- Trang N ---`; trang không có chữ ghi `--- Trang N: TRANG_SCAN, cần đọc dạng ảnh ---`), DOCX (đoạn + bảng), XLSX (mỗi sheet `### Sheet <tên>`, dòng ô cách nhau `|`), TXT/CSV. Định dạng khác → `ValueError`. CLI: `doc <path>`.
  - `list_ho_so.append_rows(data_dir: Path, project: str, rows: list[dict], template: Path | None = None) -> Path` — sổ list cộng dồn của dự án `<data>/du-an/<project>/list_ho_so.xlsx` (tạo từ `template` nếu có, giữ dòng tiêu đề), thêm dòng mới, bỏ dòng trùng `(dot, ten_ho_so)`; trả đường dẫn. `export_to(data_dir, project, out_dir) -> Path` chép bản mới nhất ra thư mục kết quả. CLI: `list-ho-so --du-an X --tu-json rows.json [--mau path] --xuat <thu-muc>`.
  - `tao_tu_mau.create_from_template(template: Path, out: Path, header_rows: int, rows: list[list]) -> Path` — XLSX: chép file mẫu, xóa giá trị (giữ định dạng) mọi ô dưới `header_rows`, bỏ gộp ô vùng dữ liệu trước khi xóa, ghi `rows`; `out` phải nằm trong một thư mục `KetQua_Agent`, nếu không → `ValueError`; không bao giờ ghi đè `template`. DOCX: chép mẫu, thay các chỗ `{{khóa}}` bằng giá trị (rows là `[[khóa, giá trị], ...]`). CLI: `tao-tu-mau --mau --ra --tieu-de N --tu-json`.
  - `tra_cuu.lookup(cfg: Config, so_hieu: str) -> dict | None` — GET `cfg.lookup_url` thêm tham số `q=<số hiệu>` (tên tham số đổi bằng `VPAK_LOOKUP_PARAM`), timeout 20 s, trả JSON; lỗi / rỗng → `None` (agent chuyển sang tra Internet). CLI: `tra-cuu "<số hiệu>"`.

- [ ] **Step 1: Viết test** (file mẫu tạo trong test bằng openpyxl, python-docx, fpdf2)

```python
def test_list_files_skips_results(tmp_path):  # Review Focus: KetQua_Agent cũ
    (tmp_path / "Đợt 4" / "KetQua_Agent" / "x").mkdir(parents=True); touch(tmp_path / "Đợt 4" / "KetQua_Agent" / "x" / "a.xlsx"); touch(tmp_path / "Đợt 4" / "To trình.pdf")
    assert [f["rel"] for f in list_files(tmp_path)] == [str(Path("Đợt 4") / "To trình.pdf")]

def test_extract_pdf_marks_scan(tmp_path): ...  # PDF 2 trang (1 có chữ "Bảo lãnh", 1 trống) → chứa "Bảo lãnh" và "TRANG_SCAN"
def test_extract_xlsx(tmp_path): ...            # chứa "### Sheet" và "Tổng cộng|1.000.000"
def test_append_rows_cumulative(tmp_path):
    append_rows(tmp_path, "HD-125", [{"dot": 3, "ten_ho_so": "Tờ trình"}])
    p = append_rows(tmp_path, "HD-125", [{"dot": 3, "ten_ho_so": "Tờ trình"}, {"dot": 4, "ten_ho_so": "Biên bản NT"}])
    assert data_rows(p) == 2
def test_template_cleared_and_not_overwritten(tmp_path): ...  # mẫu có 3 dòng dữ liệu cũ + ô gộp → file mới chỉ có rows mới, định dạng tiêu đề giữ nguyên, file mẫu không đổi (so hash)
def test_template_out_must_be_in_ketqua(tmp_path): ...       # out ngoài KetQua_Agent → ValueError
def test_lookup_failure_returns_none(cfg): assert lookup(replace(cfg, lookup_url="http://127.0.0.1:9/x?key=k"), "175/2024/NĐ-CP") is None
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết các module công cụ và `__main__.py` (argparse, lệnh con như trên).**
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Công cụ cho agent: liệt kê, đọc file, list cộng dồn, tạo file từ mẫu, tra cứu"`

---

### Task 9: Agent và lời nhắc luồng Soát thanh toán, trí nhớ, danh mục

**Files:**
- Create: `prompts/giao_viec.md` (nội dung đầy đủ), `.claude/agents/liet-ke-ho-so.md`, `doi-chieu-hop-dong.md`, `soat-cap-1.md`, `soat-cap-2.md`, `soat-cap-3.md`, `tra-cuu-van-ban.md`, `tong-hop.md`, `tri-nho/loi-hay-gap.md`, `tri-nho/sep-hay-xem.md`, `tri-nho/moi-hoc.md`, `danh-muc/ho-so-thanh-toan.md`
- Modify: `vpak/runner.py` (`build_prompt` đọc `prompts/giao_viec.md`)
- Test: `tests/test_agents.py`

**Interfaces:**
- Consumes: CLI `ghi_so` (Task 4), CLI `vpak.tools` (Task 8), `catalog.AGENTS`
- Produces:
  - `runner.build_prompt(job: str, folder: str, kind: str, note: str, out_dir: str) -> str` — thay `{job}`, `{folder}`, `{kind}`, `{note}`, `{out_dir}` trong `prompts/giao_viec.md`; `out_dir` = `<folder>/KetQua_Agent/<YYYY-MM-DD>_<job>`.
  - `prompts/giao_viec.md` quy định cho agent Giao việc: (1) chạy `python -m vpak.ghi_so` cho mọi lần giao / xong; (2) kế hoạch Soát thanh toán đúng mục 6.3 của spec (Liệt kê ∥ Tra cứu → Đối chiếu HĐ ∥ Cấp 1 ∥ Cấp 2 → Cấp 3 → Tổng hợp), giao bằng công cụ Task với `subagent_type` là id agent; (3) mẫu trong thư mục: dùng để tạo file mới; không có mẫu → `ghi_so hoi` với 2 lựa chọn "Dùng mẫu gần nhất cùng loại" / "Đại ca chỉ mẫu khác"; (4) thiếu thông tin → tìm trong `<data>/du-an/<dự án>/` và `tri-nho/`, không có thì `ghi_so hoi`; câu hỏi không chặn việc khác; (5) chỉ ghi vào `{out_dir}`; (6) không kết luận "hồ sơ đạt"; (7) cuối cùng `ghi_so xong-viec` khi không còn câu hỏi mở.
  - Mỗi file agent có frontmatter `name` (đúng id trong `catalog.AGENTS`), `description`, `tools` (chỉ `Read, Glob, Grep, Bash` và, với `tong-hop`, thêm `Write, Edit`; `tra-cuu-van-ban` thêm `WebSearch, WebFetch`), thân bài tiếng Việt nêu: việc phải làm, công cụ `vpak.tools` dùng, ghi `tien-do` sau mỗi nhóm file, mỗi phát hiện ghi `phat-hien` có `--nguon`, gắn `--nhan` khi khớp trí nhớ. `soat-cap-3` đọc `tri-nho/loi-hay-gap.md` và `tri-nho/sep-hay-xem.md` và soát từng mục. `soat-cap-2` soát: số tiền bằng số – bằng chữ; số tiền, ngày, tên đơn vị, MST, số hợp đồng, số hiệu khớp giữa tờ trình, biên bản, hóa đơn, hợp đồng, bảo lãnh; thứ tự ngày hợp lý. `tong-hop` tạo file kết quả bằng `tao-tu-mau`, cộng dồn list bằng `list-ho-so`.
  - `tri-nho/loi-hay-gap.md` khởi đầu với 6 mục ở mục 6.10 của spec; `sep-hay-xem.md` với 4 mục trong bản mẫu; `moi-hoc.md` rỗng có tiêu đề. `danh-muc/ho-so-thanh-toan.md`: danh mục chia theo giai đoạn (Tạm ứng / Thanh toán từng đợt / Đợt cuối), lấy từ skill `soat-xet-ho-so-thanh-toan` của tài khoản đại ca nếu có trong phiên làm việc; nếu không có, để các mục đã biết và đánh dấu dòng `<!-- CHỜ ĐẠI CA BỔ SUNG -->` cho phần còn thiếu.
  - Khi agent ghi `decision` có nội dung là quy tắc dùng lại được, Giao việc thêm một dòng vào `tri-nho/moi-hoc.md` dạng `- <dd/mm> <job>: <quy tắc>`.

- [ ] **Step 1: Viết test**

```python
def test_agent_files_match_catalog():
    for f in Path(".claude/agents").glob("*.md"):
        fm = parse_frontmatter(f)
        assert fm["name"] in AGENTS and fm["description"] and "tools" in fm

def test_agents_use_ledger_and_sources():
    for f in Path(".claude/agents").glob("*.md"):
        body = f.read_text(encoding="utf-8")
        assert "vpak.ghi_so" in body and "--nguon" in body and "hồ sơ đạt" not in body.replace("không kết luận \"hồ sơ đạt\"", "")

def test_prompt_placeholders_filled():
    p = build_prompt("HS-0001", r"D:\Đợt 4", "tt", "", r"D:\Đợt 4\KetQua_Agent\2026-11-25_HS-0001")
    assert "{" not in p and "KetQua_Agent" in p and "HS-0001" in p

def test_memory_seeded():
    assert len([l for l in Path("tri-nho/loi-hay-gap.md").read_text(encoding="utf-8").splitlines() if l.startswith("- ")]) >= 6
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết lời nhắc, 7 file agent, trí nhớ, danh mục; thêm `build_prompt`.**
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Agent luồng Soát thanh toán, trí nhớ và danh mục hồ sơ chuẩn"`

---

### Task 10: Giao diện 3D dùng dữ liệu thật

**Files:**
- Create: `vpak/web/index.html` (dựng từ `docs/mockup/van-phong-agent-3d.html`), `vpak/web/vendor/three.min.js` (Three.js r128, giữ dòng giấy phép MIT ở đầu file)
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: API Task 7
- Produces: trang giống bản mẫu, khác ở chỗ:
  - Bỏ toàn bộ dữ liệu giả và hàm `tick` mô phỏng; mỗi 2 s gọi `GET /api/state`, dựng `S` từ phản hồi (danh mục phòng / agent lấy từ `catalog`, id agent dạng kebab).
  - Giấy bay sinh khi so sánh trạng thái mới với cũ: task chuyển `wait→run` → bay từ `giao-viec` tới agent nhận; `run→done` → bay tới `tong-hop`; job → `done` → bay tới hộp kết quả.
  - Form giao việc → `POST /api/jobs`; lỗi 400 hiện thông báo tiếng Việt dưới ô nhập. Nút "Duyệt…" → `POST /api/browse`. "Thư mục đang làm dở" lấy từ `recent`.
  - Nút trả lời câu hỏi → `POST /api/questions/{qid}/answer`.
  - Thanh token: `quota` = `null` → hiện "Chưa có số liệu" (Kế hoạch 2 điền).
  - Khung Nhớ việc ghi "Có trong bản sau"; Trí nhớ hồ sơ hiện nội dung `tri-nho/*.md` (thêm `"memory": {"loi":[...],"sep":[...],"moi":[...]}` vào `/api/state`).
  - Script nạp `vendor/three.min.js` (không phụ thuộc CDN).
  - Mất kết nối server → dải thông báo "Mất kết nối với máy chủ, đang thử lại…" ở đầu trang.

- [ ] **Step 1: Viết test** (Playwright, bỏ qua nếu không cài được: `pytest.importorskip("playwright")`; server thật trên cổng ngẫu nhiên với `cfg_fake`)

```python
def test_page_loads_and_shows_agents(live_server, page):
    errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(live_server + "/"); page.wait_for_selector(".lbl")
    assert page.locator(".lbl").count() == 13 and errors == []

def test_submit_bad_folder_shows_message(live_server, page):
    page.goto(live_server + "/"); page.fill("#folder", "Z:/khong/co"); page.click("button.go")
    assert "Không tìm thấy thư mục" in page.text_content("#cmd")

def test_new_job_appears_in_ledger(live_server, page, tmp_path): ...  # giao thư mục thật → trong 5 s có dòng HS-0001 trong #tbody
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `index.html` theo Interfaces; tải `three.min.js` r128 vào `vendor/`.**
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Giao diện văn phòng 3D nối dữ liệu thật"`

---

### Task 11: Giao việc và trả lời câu hỏi qua Telegram / chat Claude

**Files:**
- Create: `vpak/giao_viec.py`
- Modify: `CLAUDE.md` (thêm mục "Khi nhận lệnh qua Telegram")
- Test: `tests/test_giao_viec.py`

**Interfaces:**
- Consumes: `POST /api/jobs`
- Produces:
  - `giao_viec.main(argv: list[str] | None = None) -> int` — `python -m vpak.giao_viec "<thư mục>" [--loai tt|qt|qd|cd] [--ghi-chu "..."]`; POST tới `http://127.0.0.1:<port>/api/jobs`; in `Đã giao <mã việc>. Đại ca theo dõi trên dashboard.` trả `0`; server không chạy → in `Dashboard chưa chạy. Đại ca mở scripts\chay.ps1 trước.` trả `3`; 400 → in thông báo của server, trả `2`.
  - Cùng CLI: `--cau-hoi` in các câu hỏi đang mở (`qid`, mã việc, câu hỏi, 2 lựa chọn) lấy từ `/api/state`; `--tra-loi <qid> "<câu trả lời>"` gọi `POST /api/questions/{qid}/answer`, in `Đã ghi câu trả lời cho <mã việc>.` (404 → in thông báo server, trả `2`).
  - Mục mới trong `CLAUDE.md`: khi nhận tin Telegram / chat có đường dẫn thư mục thì chạy `python -m vpak.giao_viec`; khi đại ca hỏi "có gì cần quyết" thì chạy `--cau-hoi`; khi đại ca trả lời một câu hỏi thì chạy `--tra-loi`; trả lời Telegram đúng một câu ngắn; không tự làm việc soát trong phiên Telegram.

- [ ] **Step 1: Viết test** (server FastAPI thật trên cổng ngẫu nhiên; một test cho server tắt)

```python
def test_cli_submits(live_server_port, tmp_path, capsys): assert giao_viec.main([str(folder), "--port", str(live_server_port)]) == 0 and "Đã giao HS-0001" in capsys.readouterr().out
def test_cli_server_down(capsys): assert giao_viec.main(["D:/x", "--port", "1"]) == 3
def test_cli_list_and_answer(live_server_port, open_question, capsys):  # open_question: fixture ghi sẵn sự kiện question Q1
    assert giao_viec.main(["--cau-hoi", "--port", str(live_server_port)]) == 0 and "Q1" in capsys.readouterr().out
    assert giao_viec.main(["--tra-loi", "Q1", "Chấp nhận", "--port", str(live_server_port)]) == 0
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `giao_viec.py` (urllib, timeout 10 s); sửa `CLAUDE.md`.**
- [ ] **Step 4: Chạy test, thấy PASS.**
- [ ] **Step 5: Commit** — `git commit -m "Giao việc và trả lời câu hỏi từ phiên Telegram qua CLI"`

---

### Task 12: Cài đặt và kiểm tra môi trường trên laptop

**Files:**
- Create: `vpak/kiem_tra.py`, `scripts/cai_dat.ps1`, `scripts/chay.ps1`, `HUONG_DAN.md`
- Test: `tests/test_kiem_tra.py`

**Interfaces:**
- Consumes: `Config`, `telegram.send_message`
- Produces:
  - `kiem_tra.checks(cfg: Config, env: Mapping[str, str]) -> list[tuple[str, bool, str]]` — (tên, đạt?, ghi chú tiếng Việt): Python ≥ 3.10; có lệnh `claude` và `claude --version` chạy được; **không** có `ANTHROPIC_API_KEY` (có thì không đạt, ghi chú "Gỡ biến này để dùng gói Claude công ty"); thư mục dữ liệu ghi được; `.env` có đủ 4 khóa; gói Python đã cài (fastapi, uvicorn, openpyxl, pdfplumber, docx); cổng `cfg.port` còn trống; Telegram `getMe` thành công (bỏ qua nếu thiếu token).
  - `kiem_tra.main() -> int` in bảng ✔/✘ và trả `0` nếu mọi mục bắt buộc đạt, `1` nếu không; thêm cờ `--gui-thu` gửi tin "Văn phòng Agent đã kết nối." qua Telegram.
  - `scripts/cai_dat.ps1`: tạo `.venv`, `pip install -e .`, chép `.env.example` → `.env` nếu chưa có, chạy `python -m vpak.kiem_tra`.
  - `scripts/chay.ps1`: kích hoạt `.venv`, chạy `python -m vpak.server`, mở `http://127.0.0.1:8765`.
  - `HUONG_DAN.md`: các bước cho đại ca trên laptop (clone, chạy `cai_dat.ps1`, điền `.env`, chạy `chay.ps1`, mở phiên Telegram `claude --channels plugin:telegram@claude-plugins-official` trong thư mục repo, thử giao một thư mục mẫu), xưng "đại ca".

- [ ] **Step 1: Viết test**

```python
def test_api_key_flagged(cfg):
    res = dict((n, (ok, note)) for n, ok, note in checks(cfg, {"ANTHROPIC_API_KEY": "sk-x"}))
    assert res["Không dùng API key"][0] is False
def test_missing_env_keys(cfg_empty): ...  # thiếu TELEGRAM_BOT_TOKEN → mục ".env đủ khóa" không đạt, ghi chú nêu tên khóa
def test_python_version_ok(cfg): ...       # mục "Python ≥ 3.10" đạt
```

- [ ] **Step 2: Chạy test, thấy FAIL.**
- [ ] **Step 3: Viết `kiem_tra.py`, hai script PowerShell, `HUONG_DAN.md`.**
- [ ] **Step 4: Chạy test, thấy PASS; chạy cả bộ `pytest -q` thấy PASS hết.**
- [ ] **Step 5: Commit** — `git commit -m "Script cài đặt, kiểm tra môi trường và hướng dẫn cho đại ca"`

---

### Nghiệm thu trên laptop (cùng đại ca, sau Task 12)

- [ ] Chạy `scripts\cai_dat.ps1`, mọi mục bắt buộc ✔; ghi lại kết quả các mục "kiểm tra trên laptop" của spec (tên công cụ trong `--allowedTools` có đúng không, hook có chạy không, skill có sẵn không).
- [ ] Giao một bộ hồ sơ thanh toán mẫu đã xóa thông tin nhạy cảm từ dashboard: thấy robot nhận việc, giấy bay, sổ cái có dòng, có ít nhất một phát hiện kèm nguồn, kết quả nằm trong `KetQua_Agent`, file gốc không đổi (so ngày sửa), Telegram nhận đúng một tin "Xong ...".
- [ ] Giao cùng bộ đó qua Telegram: nhận tin "Đã giao ...", việc hiện trên dashboard.
- [ ] Trả lời một câu hỏi trên dashboard: việc chạy tiếp, `tri-nho/moi-hoc.md` có dòng mới.
- [ ] Hỏi "có gì cần quyết" và trả lời một câu qua Telegram: câu hỏi biến mất khỏi dashboard, việc chạy tiếp.
