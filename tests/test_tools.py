import hashlib
import json
from dataclasses import replace
from pathlib import Path

import openpyxl
import pytest
from docx import Document
from fpdf import FPDF

from vpak.tools import __main__ as tools_cli
from vpak.tools.doc_file import extract_text
from vpak.tools.liet_ke import list_files
from vpak.tools.list_ho_so import append_rows, export_to
from vpak.tools.tao_tu_mau import create_from_template
from vpak.tools.tra_cuu import lookup


def touch(p: Path, data=b"x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def data_rows(path: Path) -> int:
    ws = openpyxl.load_workbook(path).active
    return sum(1 for r in ws.iter_rows(min_row=2, values_only=True) if any(v not in (None, "") for v in r))


def test_list_files_skips_results_and_lock_files(tmp_path):
    touch(tmp_path / "Đợt 4" / "KetQua_Agent" / "x" / "a.xlsx")
    touch(tmp_path / "Đợt 4" / "To trình.pdf")
    touch(tmp_path / "Đợt 4" / "~$Bang.xlsx")
    assert [f["rel"] for f in list_files(tmp_path)] == [str(Path("Đợt 4") / "To trình.pdf")]


def test_extract_pdf_marks_scan(tmp_path):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Helvetica", size=12); pdf.cell(text="Bao lanh thuc hien hop dong")
    pdf.add_page()
    path = tmp_path / "bl.pdf"; pdf.output(str(path))
    text = extract_text(path)
    assert "Bao lanh thuc hien" in text and "--- Trang 1 ---" in text and "TRANG_SCAN" in text
    assert list_files(tmp_path)[0]["pages"] == 2


def test_extract_docx(tmp_path):
    d = Document(); d.add_paragraph("Tờ trình đề nghị thanh toán đợt 3")
    t = d.add_table(rows=1, cols=2); t.cell(0, 0).text = "Giá trị"; t.cell(0, 1).text = "1.000.000"
    path = tmp_path / "tt.docx"; d.save(path)
    text = extract_text(path)
    assert "Tờ trình đề nghị thanh toán đợt 3" in text and "Giá trị | 1.000.000" in text


def test_extract_xlsx(tmp_path):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Tổng hợp"
    ws.append(["Tổng cộng", "1.000.000"]); path = tmp_path / "a.xlsx"; wb.save(path)
    text = extract_text(path)
    assert "### Sheet Tổng hợp" in text and "Tổng cộng|1.000.000" in text


def test_extract_unknown_format(tmp_path):
    touch(tmp_path / "a.dwg")
    with pytest.raises(ValueError):
        extract_text(tmp_path / "a.dwg")


def test_append_rows_cumulative(tmp_path):
    append_rows(tmp_path, "HD-125", [{"dot": 3, "ten_ho_so": "Tờ trình"}])
    p = append_rows(tmp_path, "HD-125", [{"dot": 3, "ten_ho_so": "Tờ trình"}, {"dot": 4, "ten_ho_so": "Biên bản NT"}])
    assert data_rows(p) == 2
    out = export_to(tmp_path, "HD-125", tmp_path / "KetQua_Agent" / "x")
    assert out.is_file() and data_rows(out) == 2


def _template(path: Path) -> Path:
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["STT", "Nội dung", "Số tiền"]); ws["A1"].font = openpyxl.styles.Font(bold=True)
    for i in range(3):
        ws.append([i + 1, f"Dữ liệu cũ {i}", 1000 * i])
    ws.merge_cells("B3:C3")
    wb.save(path)
    return path


def test_template_cleared_and_not_overwritten(tmp_path):
    tpl = _template(tmp_path / "Mau.xlsx")
    before = hashlib.sha256(tpl.read_bytes()).hexdigest()
    out = create_from_template(tpl, tmp_path / "KetQua_Agent" / "2026-11-26_HS-0001" / "Moi.xlsx", 1, [[1, "Mới", 5000]])
    ws = openpyxl.load_workbook(out).active
    assert ws["A1"].font.bold and [c.value for c in ws[2]] == [1, "Mới", 5000]
    assert all(v is None for row in ws.iter_rows(min_row=3, values_only=True) for v in row)
    assert hashlib.sha256(tpl.read_bytes()).hexdigest() == before


def test_template_docx_placeholders(tmp_path):
    d = Document(); d.add_paragraph("Kính gửi: {{don_vi}}"); tpl = tmp_path / "Mau.docx"; d.save(tpl)
    out = create_from_template(tpl, tmp_path / "KetQua_Agent" / "a" / "Moi.docx", 0, [["don_vi", "Ban QLDA"]])
    assert "Kính gửi: Ban QLDA" in "\n".join(p.text for p in Document(out).paragraphs)


def test_template_out_must_be_in_ketqua(tmp_path):
    tpl = _template(tmp_path / "Mau.xlsx")
    with pytest.raises(ValueError):
        create_from_template(tpl, tmp_path / "Moi.xlsx", 1, [])


def test_lookup_failure_returns_none(cfg):
    assert lookup(replace(cfg, lookup_url="http://127.0.0.1:9/x?key=k"), "175/2024/NĐ-CP") is None
    assert lookup(replace(cfg, lookup_url=""), "175/2024/NĐ-CP") is None


def test_cli_liet_ke_and_list(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path / "data"))
    touch(tmp_path / "hs" / "Bảo lãnh.pdf")
    assert tools_cli.main(["liet-ke", str(tmp_path / "hs")]) == 0
    assert "Bảo lãnh.pdf" in capsys.readouterr().out
    rows = tmp_path / "rows.json"; rows.write_text(json.dumps([{"dot": 1, "ten_ho_so": "Tờ trình"}], ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "hs" / "KetQua_Agent" / "x"
    assert tools_cli.main(["list-ho-so", "--du-an", "HD-1", "--tu-json", str(rows), "--xuat", str(out_dir)]) == 0
    assert list(out_dir.glob("*.xlsx"))
