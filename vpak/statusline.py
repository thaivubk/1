"""Status line của Claude Code: lưu hạn mức token (5 giờ / tuần) cho dashboard và in một dòng ngắn."""
from __future__ import annotations

import json
import sys
import time

from .config import load_config


def main(stdin_text: str | None = None) -> int:
    try:
        raw = sys.stdin.read() if stdin_text is None else stdin_text
        data = json.loads(raw)
        limits = data.get("rate_limits") or {}
        if limits.get("five_hour") or limits.get("seven_day"):
            out = {k: limits[k] for k in ("five_hour", "seven_day") if limits.get(k)}
            out["at"] = time.time()
            (load_config().data_dir / "quota.json").write_text(json.dumps(out), encoding="utf-8")
        parts = [f"{name} {int(float(limits[k]['used_percentage']) + 0.5)}%" for k, name in (("five_hour", "5 giờ"), ("seven_day", "tuần"))
                 if limits.get(k)]
        print("Token " + " · ".join(parts) if parts else "Văn phòng Agent")
    except Exception:
        print("Văn phòng Agent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
