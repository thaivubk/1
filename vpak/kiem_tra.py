"""Kiểm tra môi trường trên laptop: python -m vpak.kiem_tra [--gui-thu]"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import subprocess
import sys
import urllib.request
from typing import Mapping

from .config import Config, load_config
from .telegram import send_message

PACKAGES = ["fastapi", "uvicorn", "openpyxl", "pdfplumber", "docx"]


def _claude(cfg: Config) -> tuple[bool, str]:
    import tempfile
    with tempfile.TemporaryFile() as out:  # ghi ra file, tránh treo khi claude.cmd giữ ống dẫn trên Windows
        try:
            proc = subprocess.Popen(cfg.claude_cmd + ["--version"], stdin=subprocess.DEVNULL, stdout=out, stderr=out)
        except (FileNotFoundError, OSError):
            return False, "Chưa cài Claude Code hoặc lệnh claude chưa có trong PATH"
        try:
            code = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            return False, "Lệnh claude --version không trả lời sau 30 giây"
        out.seek(0)
        lines = out.read().decode("utf-8", errors="replace").strip().splitlines()
    return code == 0, lines[0] if lines else f"mã thoát {code}"


def _port_free(port: int) -> bool:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _telegram(cfg: Config) -> tuple[bool, str]:
    if not cfg.telegram_token:
        return False, "Chưa có TELEGRAM_BOT_TOKEN trong .env"
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{cfg.telegram_token}/getMe", timeout=10) as r:
            me = json.loads(r.read().decode("utf-8"))
        return bool(me.get("ok")), "Bot: @" + me.get("result", {}).get("username", "?")
    except Exception as e:
        return False, f"Không gọi được Telegram: {e}"


def checks(cfg: Config, env: Mapping[str, str]) -> list[tuple[str, bool, str, bool]]:
    """Trả danh sách (tên, đạt?, ghi chú, bắt buộc?)."""
    res: list[tuple[str, bool, str, bool]] = []
    v = sys.version_info
    res.append(("Python ≥ 3.10", v >= (3, 10), f"Đang dùng {v.major}.{v.minor}.{v.micro}", True))
    ok, note = _claude(cfg)
    res.append(("Claude Code", ok, note, True))
    has_key = "ANTHROPIC_API_KEY" in env
    res.append(("Không dùng API key", not has_key,
                "Gỡ biến này để dùng gói Claude công ty" if has_key else "Dùng gói Claude đã đăng nhập", True))
    try:
        probe = cfg.data_dir / ".kiem_tra"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        res.append(("Thư mục dữ liệu", True, str(cfg.data_dir), True))
    except OSError as e:
        res.append(("Thư mục dữ liệu", False, f"Không ghi được {cfg.data_dir}: {e}", True))
    missing = [k for k, val in (("TELEGRAM_BOT_TOKEN", cfg.telegram_token), ("TELEGRAM_CHAT_ID", cfg.telegram_chat_id),
                                ("VPAK_LOOKUP_URL", cfg.lookup_url)) if not val]
    res.append((".env đủ khóa", not missing, "Thiếu: " + ", ".join(missing) if missing else "Đủ", False))
    absent = [p for p in PACKAGES if importlib.util.find_spec(p) is None]
    res.append(("Gói Python", not absent, "Thiếu: " + ", ".join(absent) if absent else "Đủ", True))
    free = _port_free(cfg.port)
    res.append(("Cổng dashboard", free, f"Cổng {cfg.port} trống" if free else f"Cổng {cfg.port} đang bận (có thể dashboard đang chạy)", False))
    ok, note = _telegram(cfg)
    res.append(("Telegram", ok, note, False))
    return res


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    p = argparse.ArgumentParser(prog="python -m vpak.kiem_tra")
    p.add_argument("--gui-thu", action="store_true", help="Gửi tin thử qua Telegram")
    a = p.parse_args(argv)
    cfg = load_config()
    print("KIỂM TRA MÁY CHO VĂN PHÒNG AGENT (mất tối đa 1 phút)...", flush=True)
    results = checks(cfg, os.environ)
    for name, ok, note, req in results:
        print(f"{'✔' if ok else '✘'} {name}{' (bắt buộc)' if req and not ok else ''}: {note}")
    if a.gui_thu:
        print("Đã gửi tin thử Telegram." if send_message(cfg, "Văn phòng Agent đã kết nối.") else "Không gửi được tin thử Telegram.")
    failed = [n for n, ok, _, req in results if req and not ok]
    print("Máy đã sẵn sàng." if not failed else "Còn mục bắt buộc chưa đạt: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
