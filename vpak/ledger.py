"""Sổ cái JSONL: mỗi sự kiện một dòng, chỉ ghi thêm, có khóa khi nhiều tiến trình ghi."""
from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

EVENT_TYPES = {
    "job_created", "job_started", "task_assigned", "task_started", "progress", "finding",
    "question", "decision", "task_done", "job_done", "job_run_ended", "error",
    "agent_started", "agent_stopped", "notify",
}

LOCK_TIMEOUT = 5.0
LOCK_STALE = 30.0


def _dir(data_dir: Path) -> Path:
    d = Path(data_dir) / "so-cai"
    d.mkdir(parents=True, exist_ok=True)
    return d


@contextmanager
def _lock(folder: Path):
    lock = folder / ".lock"
    deadline = time.monotonic() + LOCK_TIMEOUT
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > LOCK_STALE:
                    lock.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise TimeoutError("Không lấy được khóa sổ cái")
            time.sleep(0.02)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def append_event(data_dir: Path, type: str, **fields) -> dict:
    if type not in EVENT_TYPES:
        raise ValueError(f"Loại sự kiện không hợp lệ: {type}")
    now = datetime.now()
    event = {"id": uuid.uuid4().hex, "ts": now.isoformat(timespec="seconds"), "type": type, **fields}
    line = json.dumps(event, ensure_ascii=False) + "\n"
    folder = _dir(data_dir)
    path = folder / f"{now:%Y-%m}.jsonl"
    with _lock(folder):
        with open(path, "a+b") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() > 0:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    f.write(b"\n")
            f.write(line.encode("utf-8"))
    return event


def _months_back(n: int) -> list[str]:
    now = datetime.now()
    y, m = now.year, now.month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def read_events(data_dir: Path, months: int = 2) -> list[dict]:
    folder = Path(data_dir) / "so-cai"
    events: list[dict] = []
    for name in _months_back(months):
        path = folder / f"{name}.jsonl"
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(ev, dict):
                events.append(ev)
    return events
