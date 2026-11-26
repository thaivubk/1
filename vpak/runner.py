"""Bộ chạy việc: tạo việc, chạy `claude -p` cho từng việc, hàng chờ, trả lời câu hỏi, phục hồi."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import unicodedata
from collections import deque
from datetime import date
from pathlib import Path

from .config import Config
from .ledger import _lock, append_event, read_events
from .state import build_state

PREFIX = {"tt": "HS", "qt": "HS", "qd": "VB", "cd": "CD", "bc": "BC"}
RESULT_DIR = "KetQua_Agent"


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def guess_kind(folder: Path) -> str:
    raw = str(folder).replace("\\", "/")
    parts = [_plain(p) for p in raw.split("/") if p]
    joined = "/".join(parts)
    if "congdoan" in joined or "cong doan" in joined:
        return "cd"
    if any(k in joined for k in ("vanban", "van ban", "quy-trinh", "quy trinh")):
        return "qd"
    if any(p.startswith("qt") for p in parts) or "quyet" in joined:
        return "qt"
    return "tt"


def allowed_tools(folder: str) -> list[str]:
    base = "//" + Path(folder).resolve().as_posix().lstrip("/")
    return ["Read", "Glob", "Grep", "Task", "WebSearch", "WebFetch",
            "Bash(python -m vpak.ghi_so:*)", "Bash(python -m vpak.tools:*)",
            f"Write({base}/{RESULT_DIR}/**)", f"Edit({base}/{RESULT_DIR}/**)"]


def build_prompt(job: str, folder: str, kind: str, note: str, out_dir: str, repo_dir: Path | None = None) -> str:
    repo = repo_dir or Path(__file__).resolve().parent.parent
    text = (repo / "prompts" / "giao_viec.md").read_text(encoding="utf-8")
    for key, value in {"job": job, "folder": folder, "kind": kind, "note": note or "(không có)", "out_dir": out_dir}.items():
        text = text.replace("{" + key + "}", value)
    return text


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return bool(ok) and code.value == 259
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class JobRunner:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.jobs_dir = cfg.data_dir / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.queue: deque[dict] = deque()
        self.running: dict[str, dict] = {}
        self.pending: dict[str, list[str]] = {}
        self.lock = threading.RLock()

    # ---------- tạo việc ----------
    def _next_number(self) -> int:
        path = self.jobs_dir / "counter.json"
        with _lock(self.jobs_dir):
            n = json.loads(path.read_text(encoding="utf-8"))["n"] + 1 if path.is_file() else 1
            path.write_text(json.dumps({"n": n}), encoding="utf-8")
        return n

    def submit(self, folder: str, kind: str | None = None, note: str = "") -> str:
        p = Path(folder)
        if not folder or not p.is_dir():
            raise ValueError(f"Không tìm thấy thư mục: {folder}")
        kind = kind or guess_kind(p)
        if kind not in PREFIX:
            raise ValueError(f"Loại việc không hợp lệ: {kind}")
        job = f"{PREFIX[kind]}-{self._next_number():04d}"
        title = " › ".join([x for x in p.parts if x not in (p.anchor, "/", "\\")][-2:])
        append_event(self.cfg.data_dir, "job_created", job=job, title=title, folder=str(p), kind=kind, note=note)
        with self.lock:
            self.queue.append({"job": job, "folder": str(p), "kind": kind, "note": note})
        return job

    # ---------- chạy ----------
    def pump(self) -> None:
        with self.lock:
            for job, run in list(self.running.items()):
                if run["proc"].poll() is not None:
                    self._finish(job, run)
            while self.queue and len(self.running) < self.cfg.max_parallel:
                self._start(self.queue.popleft())

    def _start(self, item: dict) -> None:
        job, folder = item["job"], item["folder"]
        if item.get("resume"):
            args = ["-p", item["message"], "--resume", item["resume"]]
        else:
            out_dir = Path(folder) / RESULT_DIR / f"{date.today():%Y-%m-%d}_{job}"
            out_dir.mkdir(parents=True, exist_ok=True)
            args = ["-p", build_prompt(job, folder, item["kind"], item.get("note", ""), str(out_dir), self.cfg.repo_dir)]
        cmd = self.cfg.claude_cmd + args + ["--output-format", "json", "--add-dir", folder, "--allowedTools", *allowed_tools(folder)]
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        env.update(VPAK_JOB_ID=job, VPAK_DATA=str(self.cfg.data_dir), PYTHONIOENCODING="utf-8")
        out_path, err_path = self.jobs_dir / f"{job}.out.json", self.jobs_dir / f"{job}.err.txt"
        out, err = open(out_path, "wb"), open(err_path, "wb")
        try:
            proc = subprocess.Popen(cmd, cwd=self.cfg.repo_dir, env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL)
        except FileNotFoundError:
            out.close(); err.close()
            append_event(self.cfg.data_dir, "error", job=job, reason="Không tìm thấy Claude Code trên máy")
            return
        except OSError as e:
            out.close(); err.close()
            append_event(self.cfg.data_dir, "error", job=job, reason=f"Không chạy được Claude Code: {e}")
            return
        (self.jobs_dir / f"{job}.pid").write_text(str(proc.pid), encoding="utf-8")
        append_event(self.cfg.data_dir, "job_started", job=job, pid=proc.pid, resume=bool(item.get("resume")))
        self.running[job] = {"proc": proc, "out": out, "err": err, "out_path": out_path, "err_path": err_path, "item": item}

    def _finish(self, job: str, run: dict) -> None:
        del self.running[job]
        run["out"].close(); run["err"].close()
        (self.jobs_dir / f"{job}.pid").unlink(missing_ok=True)
        code = run["proc"].returncode
        result: dict = {}
        for line in reversed(run["out_path"].read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                result = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
        session = result.get("session_id", "") if isinstance(result, dict) else ""
        if session:
            (self.jobs_dir / f"{job}.session").write_text(session, encoding="utf-8")
        append_event(self.cfg.data_dir, "job_run_ended", job=job, exit_code=code, session_id=session,
                     usage=result.get("usage", {}) if isinstance(result, dict) else {})
        failed = code != 0 or (isinstance(result, dict) and result.get("is_error"))
        if failed:
            err_lines = [l.strip() for l in run["err_path"].read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
            detail = err_lines[-1] if err_lines else str(result.get("result", "")) or f"mã thoát {code}"
            append_event(self.cfg.data_dir, "error", job=job, reason=f"Claude Code báo lỗi: {detail}"[:300])
            return
        if self.pending.get(job):
            self._queue_resume(job, self.pending.pop(job), run["item"]["folder"])
            return
        events = read_events(self.cfg.data_dir)
        state = build_state(events)
        open_q = [q for q in state["questions"] if q["job"] == job]
        done = any(e.get("type") == "job_done" and e.get("job") == job for e in events)
        if not open_q and not done:
            append_event(self.cfg.data_dir, "job_done", job=job, auto=True)

    def _queue_resume(self, job: str, messages: list[str], folder: str) -> None:
        session_file = self.jobs_dir / f"{job}.session"
        session = session_file.read_text(encoding="utf-8").strip() if session_file.is_file() else ""
        item = {"job": job, "folder": folder, "kind": "", "note": "", "message": "\n".join(messages), "resume": session}
        if not session:
            item.pop("resume")
            item["kind"] = guess_kind(Path(folder))
            item["note"] = "\n".join(messages)
        self.queue.append(item)

    # ---------- câu hỏi ----------
    def answer(self, qid: str, answer: str) -> None:
        events = read_events(self.cfg.data_dir)
        state = build_state(events)
        q = next((x for x in state["questions"] if x["id"] == qid), None)
        if q is None:
            raise KeyError(qid)
        job = q["job"]
        append_event(self.cfg.data_dir, "decision", job=job, qid=qid, answer=answer)
        message = f"Đại ca trả lời câu {qid}: {answer}. Làm tiếp các việc đang chờ."
        folder = next((j["folder"] for j in state["jobs"] if j["id"] == job), "")
        with self.lock:
            if job in self.running:
                self.pending.setdefault(job, []).append(message)
            else:
                self._queue_resume(job, [message], folder)

    # ---------- phục hồi ----------
    def recover(self) -> int:
        events = read_events(self.cfg.data_dir)
        created, started, ended, errored = {}, {}, {}, set()
        for e in events:
            j, t = e.get("job", ""), e.get("type")
            if t == "job_created":
                created[j] = e
            elif t == "job_started":
                started[j] = started.get(j, 0) + 1
            elif t == "job_run_ended":
                ended[j] = ended.get(j, 0) + 1
            elif t == "error":
                errored.add(j)
        n = 0
        with self.lock:
            for job, ev in created.items():
                if job in errored:
                    continue
                if job not in started:
                    self.queue.append({"job": job, "folder": ev.get("folder", ""), "kind": ev.get("kind", "tt"), "note": ev.get("note", "")})
                    n += 1
                elif started[job] > ended.get(job, 0):
                    pid_file = self.jobs_dir / f"{job}.pid"
                    pid = int(pid_file.read_text(encoding="utf-8")) if pid_file.is_file() else 0
                    if not _pid_alive(pid):
                        append_event(self.cfg.data_dir, "job_run_ended", job=job, exit_code=None, session_id="")
                        append_event(self.cfg.data_dir, "error", job=job, reason="Mất kết nối khi server khởi động lại")
                        pid_file.unlink(missing_ok=True)
                        n += 1
        return n
