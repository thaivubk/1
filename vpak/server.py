"""Server dashboard: chỉ nghe 127.0.0.1, phục vụ giao diện và API."""
from __future__ import annotations

import json
import os
import time
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel

from .catalog import AGENTS, ROOMS
from .config import Config, load_config
from .ledger import read_events
from .notifier import Notifier
from .runner import JobRunner
from .state import build_state
from .telegram import send_message

WEB = Path(__file__).resolve().parent / "web"
RECENT_LIMIT = 6


class JobIn(BaseModel):
    folder: str
    kind: str | None = None
    note: str = ""


class AnswerIn(BaseModel):
    answer: str


class OpenIn(BaseModel):
    path: str


def _default_opener(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]


def _default_browse() -> str | None:
    try:
        import tkinter
        from tkinter import filedialog
    except Exception:
        return None
    result: dict = {}

    def run() -> None:
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        result["path"] = filedialog.askdirectory(title="Chọn thư mục công việc") or None
        root.destroy()

    t = threading.Thread(target=run)
    t.start()
    t.join()
    return result.get("path")


def _memory(repo: Path, data: Path) -> dict:
    def items(name: str) -> list[str]:
        f = (data if name == "moi-hoc.md" else repo) / "tri-nho" / name
        if not f.is_file():
            return []
        return [l[2:].strip() for l in f.read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
    return {"loi": items("loi-hay-gap.md"), "sep": items("sep-hay-xem.md"), "moi": items("moi-hoc.md")}


QUOTA_MAX_AGE = 7 * 86400


def read_quota(data_dir: Path) -> dict | None:
    """Hạn mức token do status line của Claude Code ghi lại; quá 7 ngày thì bỏ."""
    try:
        q = json.loads((Path(data_dir) / "quota.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if time.time() - float(q.get("at", 0)) > QUOTA_MAX_AGE:
        return None
    return q


def snapshot(cfg: Config) -> dict:
    state = build_state(read_events(cfg.data_dir))
    recent, seen = [], set()
    for j in state["jobs"]:
        if j["folder"] and j["folder"] not in seen:
            seen.add(j["folder"])
            recent.append({"path": j["folder"], "name": j["title"], "job": j["id"], "status": j["status"]})
    state.update(catalog={"rooms": ROOMS, "agents": AGENTS}, recent=recent[:RECENT_LIMIT], quota=read_quota(cfg.data_dir),
                 memory=_memory(cfg.repo_dir, cfg.data_dir))
    return state


def create_app(cfg: Config, runner: JobRunner, notifier: Notifier | None = None, background: bool = True,
               opener: Callable[[str], None] = _default_opener,
               browse: Callable[[], str | None] = _default_browse) -> FastAPI:
    stop = threading.Event()

    def loop() -> None:
        while not stop.is_set():
            try:
                runner.pump()
                if notifier:
                    notifier.poll()
            except Exception as e:  # không để luồng nền chết
                print(f"Lỗi luồng nền: {e}", file=sys.stderr)
            stop.wait(3)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if background:
            threading.Thread(target=loop, daemon=True).start()
        yield
        stop.set()

    app = FastAPI(title="Văn phòng Agent Kế toán", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.get("/api/state")
    def get_state() -> dict:
        return snapshot(cfg)

    @app.post("/api/jobs")
    def post_job(body: JobIn) -> dict:
        try:
            job = runner.submit(body.folder.strip(), body.kind or None, body.note)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"job": job}

    @app.post("/api/questions/{qid}/answer")
    def post_answer(qid: str, body: AnswerIn) -> dict:
        try:
            runner.answer(qid, body.answer)
        except KeyError:
            raise HTTPException(status_code=404, detail="Câu hỏi đã được trả lời hoặc không tồn tại")
        return {"ok": True}

    @app.post("/api/browse")
    def post_browse() -> dict:
        return {"path": browse()}

    @app.post("/api/open")
    def post_open(body: OpenIn) -> dict:
        target = Path(body.path).resolve()
        roots = [Path(j["folder"]).resolve() for j in build_state(read_events(cfg.data_dir))["jobs"] if j["folder"]]
        if not any(target == r or r in target.parents for r in roots):
            raise HTTPException(status_code=403, detail="Chỉ mở được thư mục của các việc đã giao")
        opener(str(target))
        return {"ok": True}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (WEB / "index.html").read_text(encoding="utf-8")

    if (WEB / "vendor").is_dir():
        app.mount("/vendor", StaticFiles(directory=WEB / "vendor"), name="vendor")
    return app


def main() -> None:
    import uvicorn

    cfg = load_config()
    runner = JobRunner(cfg)
    notifier = Notifier(cfg.data_dir, lambda text: send_message(cfg, text))
    runner.recover()
    print(f"Văn phòng Agent đang chạy: http://127.0.0.1:{cfg.port}")
    uvicorn.run(create_app(cfg, runner, notifier), host="127.0.0.1", port=cfg.port, log_level="warning")


if __name__ == "__main__":
    main()
