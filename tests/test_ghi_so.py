import pytest

from vpak import ghi_so
from vpak.ledger import read_events


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    monkeypatch.setenv("VPAK_JOB_ID", "HS-0001")
    return tmp_path


def test_phat_hien_requires_nguon(env):
    assert ghi_so.main(["phat-hien", "--task", "HS-0001.1", "--agent", "soat-cap-2", "--text", "Sai ngày"]) == 2
    assert ghi_so.main(["phat-hien", "--task", "HS-0001.1", "--agent", "soat-cap-2", "--text", "Sai ngày",
                        "--nguon", "BB.pdf tr1", "--nhan", "Lỗi hay gặp"]) == 0
    ev = read_events(env)[-1]
    assert (ev["type"], ev["nguon"], ev["nhan"], ev["job"]) == ("finding", "BB.pdf tr1", "Lỗi hay gặp", "HS-0001")


def test_hoi_prints_qid(env, capsys):
    assert ghi_so.main(["hoi", "--task", "HS-0001.1", "--agent", "soat-cap-2", "--q", "Chấp nhận bản scan?",
                        "--chon", "Chấp nhận", "--chon", "Yêu cầu bản gốc"]) == 0
    ev = read_events(env)[-1]
    assert ev["type"] == "question" and ev["choices"] == ["Chấp nhận", "Yêu cầu bản gốc"]
    assert ev["qid"].startswith("Q") and ev["qid"] in capsys.readouterr().out


def test_giao_bat_dau_tien_do_xong(env):
    assert ghi_so.main(["giao", "--task", "HS-0001.1", "--agent", "soat-cap-1", "--desc", "Soát cấp 1"]) == 0
    assert ghi_so.main(["bat-dau", "--task", "HS-0001.1", "--agent", "soat-cap-1"]) == 0
    assert ghi_so.main(["tien-do", "--task", "HS-0001.1", "--pct", "40", "--ghi-chu", "12/23 hồ sơ"]) == 0
    assert ghi_so.main(["xong", "--task", "HS-0001.1", "--file", "Phieu.xlsx"]) == 0
    assert ghi_so.main(["xong-viec"]) == 0
    assert [e["type"] for e in read_events(env)] == ["task_assigned", "task_started", "progress", "task_done", "job_done"]


def test_loi(env):
    assert ghi_so.main(["loi", "--text", "Không đọc được file"]) == 0
    assert read_events(env)[-1]["reason"] == "Không đọc được file"


def test_missing_job(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    monkeypatch.delenv("VPAK_JOB_ID", raising=False)
    assert ghi_so.main(["bat-dau", "--task", "x", "--agent", "soat-cap-1"]) == 2
    assert "mã việc" in capsys.readouterr().err


def test_bad_pct(env):
    assert ghi_so.main(["tien-do", "--task", "t", "--pct", "abc"]) == 2
