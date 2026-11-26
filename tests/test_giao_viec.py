from conftest import events_of, make_folder
from vpak import giao_viec
from vpak.ledger import append_event


def port_of(url: str) -> str:
    return url.rsplit(":", 1)[1]


def test_cli_submits(live, tmp_path, capsys):
    url, runner, cfg = live
    assert giao_viec.main([str(make_folder(tmp_path)), "--port", port_of(url)]) == 0
    assert "Đã giao HS-0001" in capsys.readouterr().out


def test_cli_bad_folder(live, capsys):
    assert giao_viec.main(["Z:/khong/co", "--port", port_of(live[0])]) == 2
    assert "Không tìm thấy thư mục" in capsys.readouterr().out


def test_cli_server_down(capsys):
    assert giao_viec.main(["D:/x", "--port", "1"]) == 3
    assert "Dashboard chưa chạy" in capsys.readouterr().out


def test_cli_list_and_answer(live, tmp_path, capsys):
    url, runner, cfg = live
    job = runner.submit(str(make_folder(tmp_path)))
    append_event(cfg.data_dir, "question", job=job, task=job + ".1", agent="soat-cap-2", qid="Q1", q="Chấp nhận bản scan?", choices=["Có", "Không"])
    assert giao_viec.main(["--cau-hoi", "--port", port_of(url)]) == 0
    out = capsys.readouterr().out
    assert "Q1" in out and "Chấp nhận bản scan?" in out
    assert giao_viec.main(["--tra-loi", "Q1", "Có", "--port", port_of(url)]) == 0
    assert "Đã ghi câu trả lời cho " + job in capsys.readouterr().out
    assert events_of(cfg, job, "decision")[-1]["answer"] == "Có"
    assert giao_viec.main(["--tra-loi", "Q1", "Có", "--port", port_of(url)]) == 2


def test_cli_no_questions(live, capsys):
    assert giao_viec.main(["--cau-hoi", "--port", port_of(live[0])]) == 0
    assert "Không có câu hỏi" in capsys.readouterr().out
