"""Liệt kê file hồ sơ (cả thư mục con), bỏ qua thư mục kết quả cũ và file tạm của Office."""
from __future__ import annotations

from pathlib import Path

from . import RESULT_DIR


def _pages(path: Path) -> int | None:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return len(pdf.pages)
    except Exception:
        return None


def list_files(folder: Path) -> list[dict]:
    folder = Path(folder)
    out = []
    for p in folder.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(folder)
        if RESULT_DIR in rel.parts or p.name.startswith("~$"):
            continue
        ext = p.suffix.lower().lstrip(".")
        out.append({"rel": str(rel), "ext": ext, "size": p.stat().st_size, "pages": _pages(p) if ext == "pdf" else None})
    return sorted(out, key=lambda f: f["rel"])
