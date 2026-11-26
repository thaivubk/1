"""Tạo file mới giống mẫu: chép định dạng, xóa dữ liệu cũ, nhập dữ liệu mới. Không sửa file mẫu."""
from __future__ import annotations

import shutil
from pathlib import Path

from . import RESULT_DIR, ensure_result_path


def _xlsx(out: Path, header_rows: int, rows: list[list]) -> None:
    import openpyxl
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    for rng in list(ws.merged_cells.ranges):
        if rng.max_row > header_rows:
            ws.unmerge_cells(str(rng))
    for row in ws.iter_rows(min_row=header_rows + 1):
        for c in row:
            c.value = None
    for r, values in enumerate(rows, header_rows + 1):
        for col, v in enumerate(values, 1):
            ws.cell(row=r, column=col, value=v)
    wb.save(out)


def _replace_in_paragraph(p, mapping: dict) -> None:
    text = "".join(r.text for r in p.runs)
    new = text
    for k, v in mapping.items():
        new = new.replace("{{" + k + "}}", str(v))
    if new != text and p.runs:
        p.runs[0].text = new
        for r in p.runs[1:]:
            r.text = ""


def _docx(out: Path, rows: list[list]) -> None:
    from docx import Document
    mapping = {str(r[0]): r[1] for r in rows if len(r) >= 2}
    d = Document(out)
    for p in d.paragraphs:
        _replace_in_paragraph(p, mapping)
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_in_paragraph(p, mapping)
    d.save(out)


def create_from_template(template: Path, out: Path, header_rows: int, rows: list[list]) -> Path:
    template, out = Path(template), ensure_result_path(Path(out))
    if out.resolve() == template.resolve():
        raise ValueError("Không được ghi đè file mẫu")
    ext = template.suffix.lower()
    if ext not in (".xlsx", ".docx"):
        raise ValueError(f"Chưa hỗ trợ mẫu định dạng {ext}")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, out)
    if ext == ".xlsx":
        _xlsx(out, header_rows, rows)
    else:
        _docx(out, rows)
    return out
