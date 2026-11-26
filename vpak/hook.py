"""Hook Claude Code: ghi sổ khi agent con bắt đầu / kết thúc. Không bao giờ làm hỏng phiên chạy."""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime

from .config import load_config
from .ledger import append_event

MAP = {"SubagentStart": "agent_started", "SubagentStop": "agent_stopped"}


def main(stdin_text: str | None = None) -> int:
    try:
        data = load_config().data_dir
    except Exception:
        return 0
    try:
        raw = sys.stdin.read() if stdin_text is None else stdin_text
        payload = json.loads(raw)
        typ = MAP.get(payload.get("hook_event_name", ""))
        if typ:
            append_event(data, typ, job=os.environ.get("VPAK_JOB_ID", ""), agent=payload.get("agent_type", ""),
                         agent_id=payload.get("agent_id", ""), session_id=payload.get("session_id", ""))
    except Exception:
        try:
            with open(data / "hook-errors.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat(timespec='seconds')} {traceback.format_exc()}\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
