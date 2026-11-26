import multiprocessing
from datetime import datetime

import pytest

from vpak.ledger import append_event, read_events


def _write_50(path):
    for i in range(50):
        append_event(path, "progress", job="HS-0001", task="t", pct=i)


def test_roundtrip_unicode(tmp_path):
    append_event(tmp_path, "finding", job="HS-0001", text="Bảo lãnh thiếu ngày", nguon="BL.pdf, trang 1")
    ev = read_events(tmp_path)[-1]
    assert ev["text"] == "Bảo lãnh thiếu ngày" and ev["type"] == "finding" and "ts" in ev and ev["id"]


def test_monthly_file(tmp_path):
    append_event(tmp_path, "job_created", job="HS-0001")
    files = list((tmp_path / "so-cai").glob("*.jsonl"))
    assert [f.name for f in files] == [datetime.now().strftime("%Y-%m") + ".jsonl"]


def test_unicode_not_escaped_on_disk(tmp_path):
    append_event(tmp_path, "finding", job="HS-0001", text="Đợt 4")
    raw = next((tmp_path / "so-cai").glob("*.jsonl")).read_text(encoding="utf-8")
    assert "Đợt 4" in raw


def test_concurrent_processes(tmp_path):
    with multiprocessing.get_context("spawn").Pool(4) as p:
        p.map(_write_50, [tmp_path] * 4)
    assert len(read_events(tmp_path)) == 200


def test_torn_last_line_skipped(tmp_path):
    append_event(tmp_path, "job_created", job="HS-0001")
    f = next((tmp_path / "so-cai").glob("*.jsonl"))
    f.write_text(f.read_text(encoding="utf-8") + '{"type": "fin', encoding="utf-8")
    assert len(read_events(tmp_path)) == 1


def test_append_after_torn_line_still_readable(tmp_path):
    append_event(tmp_path, "job_created", job="HS-0001")
    f = next((tmp_path / "so-cai").glob("*.jsonl"))
    f.write_text(f.read_text(encoding="utf-8") + '{"type": "fin', encoding="utf-8")
    append_event(tmp_path, "job_done", job="HS-0001")
    assert [e["type"] for e in read_events(tmp_path)] == ["job_created", "job_done"]


def test_unknown_type(tmp_path):
    with pytest.raises(ValueError):
        append_event(tmp_path, "abc")
