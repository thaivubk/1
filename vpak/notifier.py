"""Theo dõi sổ cái, gửi tin Telegram ngắn gọn khi xong việc, chờ quyết, hoặc lỗi."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .ledger import append_event, read_events

REASON_LIMIT = 120


class Notifier:
    def __init__(self, data_dir: Path, send: Callable[[str], bool]):
        self.data_dir = Path(data_dir)
        self.send = send
        self.cursor_file = self.data_dir / "notifier.json"

    def _load(self) -> dict | None:
        try:
            return json.loads(self.cursor_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _save(self, ev: dict) -> None:
        self.cursor_file.write_text(json.dumps({"id": ev["id"], "ts": ev["ts"]}), encoding="utf-8")

    def poll(self) -> int:
        events = read_events(self.data_dir)
        cursor = self._load()
        if cursor is None:
            if events:
                self._save(events[-1])
            else:
                self.cursor_file.write_text(json.dumps({"id": "", "ts": ""}), encoding="utf-8")
            return 0
        ids = [e.get("id") for e in events]
        if cursor.get("id") in ids:
            new = events[ids.index(cursor["id"]) + 1:]
        else:
            new = [e for e in events if e.get("ts", "") > cursor.get("ts", "")]
        sent = 0
        for i, ev in enumerate(new):
            msg = self._message(ev, events[: len(events) - len(new) + i + 1])
            if msg:
                ok = self.send(msg)
                append_event(self.data_dir, "notify", job=ev.get("job", ""), text=msg, ok=bool(ok))
                sent += 1 if ok else 0
        if new:
            self._save(new[-1])
        return sent

    @staticmethod
    def _message(ev: dict, history: list[dict]) -> str | None:
        job, typ = ev.get("job", ""), ev.get("type")
        if typ == "job_done":
            n = sum(1 for e in history if e.get("type") == "finding" and e.get("job") == job)
            return f"Xong {job}: {n} phát hiện, kết quả đã lưu."
        if typ == "job_run_ended":
            asked = {e.get("qid") for e in history if e.get("type") == "question" and e.get("job") == job}
            answered = {e.get("qid") for e in history if e.get("type") == "decision"}
            k = len(asked - answered)
            return f"{job} chờ đại ca quyết {k} câu." if k else None
        if typ == "error":
            return f"{job} gặp lỗi: {str(ev.get('reason', ''))[:REASON_LIMIT]}"
        return None
