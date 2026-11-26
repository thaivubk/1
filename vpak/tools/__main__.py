"""python -m vpak.tools <lệnh>: doc | liet-ke | list-ho-so | tao-tu-mau | tra-cuu"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..config import load_config
from .doc_file import extract_text
from .liet_ke import list_files
from .list_ho_so import append_rows, export_to
from .tao_tu_mau import create_from_template
from .tra_cuu import lookup


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    p = argparse.ArgumentParser(prog="python -m vpak.tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("doc"); s.add_argument("path")
    s = sub.add_parser("liet-ke"); s.add_argument("folder")
    s = sub.add_parser("list-ho-so"); s.add_argument("--du-an", required=True); s.add_argument("--tu-json", required=True)
    s.add_argument("--mau", default=None); s.add_argument("--xuat", required=True)
    s = sub.add_parser("tao-tu-mau"); s.add_argument("--mau", required=True); s.add_argument("--ra", required=True)
    s.add_argument("--tieu-de", type=int, default=1); s.add_argument("--tu-json", required=True)
    s = sub.add_parser("tra-cuu"); s.add_argument("so_hieu")
    try:
        a = p.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    try:
        if a.cmd == "doc":
            print(extract_text(Path(a.path)))
        elif a.cmd == "liet-ke":
            for f in list_files(Path(a.folder)):
                pages = f" | {f['pages']} trang" if f["pages"] else ""
                print(f"{f['rel']} | {f['ext']} | {f['size']} byte{pages}")
        elif a.cmd == "list-ho-so":
            rows = json.loads(Path(a.tu_json).read_text(encoding="utf-8"))
            data = load_config().data_dir
            append_rows(data, a.du_an, rows, Path(a.mau) if a.mau else None)
            print(f"Đã cộng dồn list hồ sơ: {export_to(data, a.du_an, Path(a.xuat))}")
        elif a.cmd == "tao-tu-mau":
            rows = json.loads(Path(a.tu_json).read_text(encoding="utf-8"))
            print(f"Đã tạo: {create_from_template(Path(a.mau), Path(a.ra), a.tieu_de, rows)}")
        else:
            res = lookup(load_config(), a.so_hieu)
            print(json.dumps(res, ensure_ascii=False, indent=1) if res else "KHONG_CO_KET_QUA: chuyển sang tra Internet")
    except (ValueError, OSError) as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
