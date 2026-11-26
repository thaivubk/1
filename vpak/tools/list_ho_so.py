"""List hồ sơ cộng dồn theo dự án, lưu trong thư mục dữ liệu."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import openpyxl

HEADER = ["STT", "Đợt", "Tên hồ sơ", "File", "Ghi chú"]


def _safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip() or "du-an"


def _path(data_dir: Path, project: str) -> Path:
    return Path(data_dir) / "du-an" / _safe(project) / "list_ho_so.xlsx"


def append_rows(data_dir: Path, project: str, rows: list, template: Path | None = None) -> Path:
    """rows: dict (5 cột chuẩn) hoặc list giá trị đúng thứ tự cột của mẫu list hồ sơ."""
    path = _path(data_dir, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if template and Path(template).is_file():
            shutil.copyfile(template, path)
            wb = openpyxl.load_workbook(path)
            ws = wb.active
            for rng in list(ws.merged_cells.ranges):
                if rng.min_row > 1:
                    ws.unmerge_cells(str(rng))
            for row in ws.iter_rows(min_row=2):
                for c in row:
                    c.value = None
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "List hồ sơ"
            ws.append(HEADER)
        wb.save(path)
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    existing = set()
    last = 1
    for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if any(v not in (None, "") for v in r[:3]):
            existing.add((str(r[1]), str(r[2])))
            last = i
    for row in rows:
        if isinstance(row, (list, tuple)):
            values = list(row)
            key = (str(values[1] if len(values) > 1 else ""), str(values[2] if len(values) > 2 else ""))
        else:
            values = None
            key = (str(row.get("dot", "")), str(row.get("ten_ho_so", "")))
        if key in existing:
            continue
        existing.add(key)
        last += 1
        if values is None:
            values = [last - 1, row.get("dot", ""), row.get("ten_ho_so", ""), row.get("file", ""), row.get("ghi_chu", "")]
        for col, v in enumerate(values, 1):
            ws.cell(row=last, column=col, value=v)
    wb.save(path)
    return path


def export_to(data_dir: Path, project: str, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"List_ho_so_{_safe(project)}.xlsx"
    shutil.copyfile(_path(data_dir, project), target)
    return target
