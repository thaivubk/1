from pathlib import Path

import openpyxl

from vpak.catalog import AGENTS
from vpak.runner import build_prompt
from vpak.tools.list_ho_so import append_rows

FLOW = {"liet-ke-ho-so", "doi-chieu-hop-dong", "soat-cap-1", "soat-cap-2", "soat-cap-3", "tra-cuu-van-ban", "tong-hop"}


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    head = text.split("---\n")[1]
    return {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in head.splitlines() if ":" in line)}


def test_agent_files_match_catalog():
    files = list(Path(".claude/agents").glob("*.md"))
    names = set()
    for f in files:
        fm = parse_frontmatter(f)
        assert fm["name"] in AGENTS and fm["description"] and fm["tools"]
        assert f.stem == fm["name"]
        names.add(fm["name"])
    assert names == FLOW


def test_agents_use_ledger_and_sources():
    for f in Path(".claude/agents").glob("*.md"):
        body = f.read_text(encoding="utf-8")
        assert "vpak.ghi_so" in body and "--nguon" in body, f.name
        assert "hồ sơ đạt" not in body.replace('không kết luận "hồ sơ đạt"', ""), f.name


def test_only_tong_hop_writes():
    for f in Path(".claude/agents").glob("*.md"):
        tools = parse_frontmatter(f)["tools"]
        assert ("Write" in tools) == (f.stem == "tong-hop"), f.name


def test_prompt_placeholders_filled():
    p = build_prompt("HS-0001", r"D:\Đợt 4", "tt", "", r"D:\Đợt 4\KetQua_Agent\2026-11-25_HS-0001")
    assert "{" not in p and "}" not in p and "KetQua_Agent" in p and "HS-0001" in p
    for agent in FLOW:
        assert agent in p, agent
    assert "xong-viec" in p and "hoi" in p


def test_memory_seeded():
    loi = [l for l in Path("tri-nho/loi-hay-gap.md").read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
    sep = [l for l in Path("tri-nho/sep-hay-xem.md").read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
    assert len(loi) >= 6 and len(sep) >= 4 and Path("tri-nho/moi-hoc.md").is_file()


def test_checklist_has_stages():
    text = Path("danh-muc/ho-so-thanh-toan.md").read_text(encoding="utf-8")
    for stage in ("Tạm ứng", "Thanh toán từng đợt", "Đợt cuối"):
        assert stage in text


def test_append_rows_accepts_full_template_rows(tmp_path):
    tpl = tmp_path / "List.xlsx"
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["STT", "Danh mục hồ sơ", "Số văn bản", "Ngày ban hành", "THIẾU", "Nhận xét chuyên viên"]); wb.save(tpl)
    row = [1, "Bảo lãnh thực hiện HĐ", "BL-01", "01/11/2026", "", "Thiếu ngày hết hiệu lực"]
    p = append_rows(tmp_path / "data", "HD-1", [row, row], template=tpl)
    ws = openpyxl.load_workbook(p).active
    assert [c.value for c in ws[1]][:2] == ["STT", "Danh mục hồ sơ"]
    assert [c.value for c in ws[2]] == [v if v != "" else None for v in row] and ws.max_row == 2
