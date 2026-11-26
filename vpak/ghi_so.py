"""CLI cho agent ghi sổ cái: python -m vpak.ghi_so <lệnh> ..."""
from __future__ import annotations

import argparse
import os
import sys
import uuid

from .config import load_config
from .ledger import append_event


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m vpak.ghi_so", description="Ghi sổ cái công việc")
    p.add_argument("--job", default=None, help="Mã việc (mặc định lấy VPAK_JOB_ID)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("giao"); s.add_argument("--task", required=True); s.add_argument("--agent", required=True); s.add_argument("--desc", required=True)
    s = sub.add_parser("bat-dau"); s.add_argument("--task", required=True); s.add_argument("--agent", required=True)
    s = sub.add_parser("tien-do"); s.add_argument("--task", required=True); s.add_argument("--pct", required=True); s.add_argument("--ghi-chu", default="")
    s = sub.add_parser("phat-hien"); s.add_argument("--task", required=True); s.add_argument("--agent", required=True)
    s.add_argument("--text", required=True); s.add_argument("--nguon", default=""); s.add_argument("--nhan", default="")
    s = sub.add_parser("hoi"); s.add_argument("--task", required=True); s.add_argument("--agent", required=True)
    s.add_argument("--q", required=True); s.add_argument("--chon", action="append", default=[])
    s = sub.add_parser("xong"); s.add_argument("--task", required=True); s.add_argument("--file", default="")
    s = sub.add_parser("loi"); s.add_argument("--text", required=True)
    sub.add_parser("xong-viec")
    return p


def _err(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    try:
        a = _parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    job = a.job or os.environ.get("VPAK_JOB_ID", "")
    if not job:
        return _err("Thiếu mã việc: đặt biến VPAK_JOB_ID hoặc dùng --job.")
    data = load_config().data_dir
    if a.cmd == "giao":
        ev = append_event(data, "task_assigned", job=job, task=a.task, agent=a.agent, desc=a.desc)
    elif a.cmd == "bat-dau":
        ev = append_event(data, "task_started", job=job, task=a.task, agent=a.agent)
    elif a.cmd == "tien-do":
        try:
            pct = int(float(a.pct))
        except ValueError:
            return _err("--pct phải là số từ 0 đến 100.")
        ev = append_event(data, "progress", job=job, task=a.task, pct=max(0, min(100, pct)), ghi_chu=a.ghi_chu)
    elif a.cmd == "phat-hien":
        if not a.nguon.strip():
            return _err("Phát hiện phải có --nguon (file nào, trang hoặc dòng nào).")
        ev = append_event(data, "finding", job=job, task=a.task, agent=a.agent, text=a.text, nguon=a.nguon, nhan=a.nhan)
    elif a.cmd == "hoi":
        qid = "Q" + uuid.uuid4().hex[:6].upper()
        ev = append_event(data, "question", job=job, task=a.task, agent=a.agent, qid=qid, q=a.q, choices=a.chon[:2])
        print(qid)
    elif a.cmd == "xong":
        ev = append_event(data, "task_done", job=job, task=a.task, file=a.file)
    elif a.cmd == "loi":
        ev = append_event(data, "error", job=job, reason=a.text)
    else:
        ev = append_event(data, "job_done", job=job)
    print(f"Đã ghi: {ev['type']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
