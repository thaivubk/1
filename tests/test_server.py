import pytest
from fastapi.testclient import TestClient

from conftest import events_of, make_folder
from vpak.ledger import append_event
from vpak.runner import JobRunner
from vpak.server import create_app


@pytest.fixture
def setup(cfg_fake):
    runner = JobRunner(cfg_fake)
    opened = []
    app = create_app(cfg_fake, runner, background=False, opener=opened.append, browse=lambda: "D:/Chon")
    with TestClient(app) as c:
        yield c, runner, cfg_fake, opened


def test_state_shape(setup):
    c = setup[0]
    r = c.get("/api/state")
    body = r.json()
    assert r.status_code == 200 and len(body["catalog"]["agents"]) == 13 and len(body["catalog"]["rooms"]) == 6
    assert body["quota"] is None and body["recent"] == [] and "kpis" in body


def test_create_job_and_recent(setup, tmp_path):
    c, runner, cfg, _ = setup
    folder = make_folder(tmp_path)
    r = c.post("/api/jobs", json={"folder": str(folder)})
    assert r.status_code == 200 and r.json() == {"job": "HS-0001"}
    rec = c.get("/api/state").json()["recent"]
    assert rec[0]["path"] == str(folder) and rec[0]["job"] == "HS-0001"


def test_bad_folder(setup):
    r = setup[0].post("/api/jobs", json={"folder": "Z:/khong/co"})
    assert r.status_code == 400 and "Không tìm thấy thư mục" in r.json()["detail"]


def test_answer_unknown(setup):
    r = setup[0].post("/api/questions/Q404/answer", json={"answer": "x"})
    assert r.status_code == 404 and r.json()["detail"] == "Câu hỏi đã được trả lời hoặc không tồn tại"


def test_answer_open_question(setup, tmp_path):
    c, runner, cfg, _ = setup
    job = runner.submit(str(make_folder(tmp_path)))
    append_event(cfg.data_dir, "question", job=job, task=job + ".1", agent="soat-cap-2", qid="Q1", q="?", choices=["a", "b"])
    assert c.post("/api/questions/Q1/answer", json={"answer": "a"}).json() == {"ok": True}
    assert events_of(cfg, job, "decision")[-1]["answer"] == "a"


def test_open_outside_jobs_forbidden(setup, tmp_path):
    assert setup[0].post("/api/open", json={"path": str(tmp_path)}).status_code == 403


def test_open_inside_job_folder(setup, tmp_path):
    c, runner, cfg, opened = setup
    folder = make_folder(tmp_path)
    runner.submit(str(folder))
    target = folder / "KetQua_Agent"
    target.mkdir()
    assert c.post("/api/open", json={"path": str(target)}).status_code == 200 and opened == [str(target)]


def test_browse(setup):
    assert setup[0].post("/api/browse").json() == {"path": "D:/Chon"}


def test_index_served(setup):
    assert "Văn phòng Agent" in setup[0].get("/").text


def test_state_has_memory(setup):
    mem = setup[0].get("/api/state").json()["memory"]
    assert len(mem["loi"]) >= 6 and len(mem["sep"]) >= 4 and isinstance(mem["moi"], list)
