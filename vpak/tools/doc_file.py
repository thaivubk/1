"""Trích chữ từ PDF, Word, Excel, văn bản thường để agent đọc."""
from __future__ import annotations

from pathlib import Path


def _pdf(path: Path) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = (page.extract_text() or "").strip()
            parts.append(f"--- Trang {i} ---\n{text}" if text else f"--- Trang {i}: TRANG_SCAN, cần đọc dạng ảnh ---")
    return "\n".join(parts)


def _docx(path: Path) -> str:
    from docx import Document
    d = Document(path)
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for t in d.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(parts)


def _xlsx(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append(f"### Sheet {ws.title}")
        for row in ws.iter_rows(values_only=True):
            if any(v not in (None, "") for v in row):
                parts.append("|".join("" if v is None else str(v) for v in row))
    wb.close()
    return "\n".join(parts)


READERS = {"pdf": _pdf, "docx": _docx, "xlsx": _xlsx, "xlsm": _xlsx}


def extract_text(path: Path, max_chars: int = 60000) -> str:
    path = Path(path)
    ext = path.suffix.lower().lstrip(".")
    if ext in READERS:
        text = READERS[ext](path)
    elif ext in ("txt", "csv", "md"):
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Chưa đọc được định dạng .{ext}: {path.name}")
    return text if len(text) <= max_chars else text[:max_chars] + "\n...(đã cắt bớt)"
