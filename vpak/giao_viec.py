"""Giao việc / xem câu hỏi / trả lời câu hỏi từ phiên Telegram hoặc cửa sổ lệnh.

python -m vpak.giao_viec "<thư mục>" [--loai tt|qt|qd|cd] [--ghi-chu "..."]
python -m vpak.giao_viec --cau-hoi
python -m vpak.giao_viec --tra-loi <qid> "<câu trả lời>"
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from .config import load_config

DOWN = "Dashboard chưa chạy. Đại ca mở scripts\\chay.ps1 trước."


class ServerDown(Exception):
    pass


def _call(port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"detail": f"Lỗi {e.code}"}
    except (urllib.error.URLError, OSError) as e:
        raise ServerDown(str(e))


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    p = argparse.ArgumentParser(prog="python -m vpak.giao_viec")
    p.add_argument("folder", nargs="?")
    p.add_argument("--loai", choices=["tt", "qt", "qd", "cd"], default=None)
    p.add_argument("--ghi-chu", default="")
    p.add_argument("--cau-hoi", action="store_true")
    p.add_argument("--tra-loi", nargs=2, metavar=("QID", "CAU_TRA_LOI"))
    p.add_argument("--port", type=int, default=None)
    try:
        a = p.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    port = a.port or load_config().port
    try:
        if a.cau_hoi:
            _, state = _call(port, "GET", "/api/state")
            qs = state.get("questions", [])
            if not qs:
                print("Không có câu hỏi nào đang chờ đại ca.")
            for q in qs:
                print(f"{q['id']} | {q['job']} | {q['q']} | Lựa chọn: {' / '.join(q.get('choices', []))}")
            return 0
        if a.tra_loi:
            qid, ans = a.tra_loi
            _, state = _call(port, "GET", "/api/state")
            job = next((q["job"] for q in state.get("questions", []) if q["id"] == qid), "")
            code, body = _call(port, "POST", f"/api/questions/{urllib.parse.quote(qid)}/answer", {"answer": ans})
            if code != 200:
                print(body.get("detail", f"Lỗi {code}"))
                return 2
            print(f"Đã ghi câu trả lời cho {job}.")
            return 0
        if not a.folder:
            print("Thiếu đường dẫn thư mục công việc.")
            return 2
        code, body = _call(port, "POST", "/api/jobs", {"folder": a.folder, "kind": a.loai, "note": a.ghi_chu})
        if code != 200:
            print(body.get("detail", f"Lỗi {code}"))
            return 2
        print(f"Đã giao {body['job']}. Đại ca theo dõi trên dashboard.")
        return 0
    except ServerDown:
        print(DOWN)
        return 3


if __name__ == "__main__":
    sys.exit(main())
