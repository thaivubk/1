from itertools import count

from vpak.state import build_state

_n = count()


def E(type, **f):
    i = next(_n)
    return {"id": f"e{i}", "ts": f"2026-11-26T08:{i // 60:02d}:{i % 60:02d}", "type": type, **f}


def base():
    return [E("job_created", job="HS-0001", title="Dot4", folder="D:/x", kind="tt", note=""),
            E("task_assigned", job="HS-0001", task="HS-0001.1", agent="soat-cap-2", desc="Soát cấp 2"),
            E("task_started", job="HS-0001", task="HS-0001.1", agent="soat-cap-2")]


def test_flow_states():
    s = build_state(base() + [E("progress", job="HS-0001", task="HS-0001.1", pct=40)])
    assert s["agents"]["soat-cap-2"] == {"st": "run", "task": "HS-0001.1", "pct": 40, "done": 0}
    assert s["agents"]["doc-so-cai"]["st"] == "idle"
    assert len(s["agents"]) == 13


def test_question_then_decision():
    ev = base() + [E("question", job="HS-0001", task="HS-0001.1", agent="soat-cap-2", qid="Q1",
                     q="Chấp nhận bản scan?", choices=["Chấp nhận", "Yêu cầu bản gốc"])]
    s = build_state(ev)
    assert s["questions"][0]["id"] == "Q1" and s["jobs"][0]["status"] == "review"
    assert s["agents"]["soat-cap-2"]["st"] == "review"
    s2 = build_state(ev + [E("decision", job="HS-0001", qid="Q1", answer="Chấp nhận")])
    assert s2["questions"] == [] and s2["agents"]["soat-cap-2"]["st"] == "run"


def test_finding_counts_and_kpis():
    s = build_state(base() + [E("finding", job="HS-0001", task="HS-0001.1", agent="soat-cap-2",
                                text="Sai ngày", nguon="BB.pdf tr1", nhan="Lỗi hay gặp")])
    t = s["jobs"][0]["tasks"][0]
    assert s["kpis"]["finds"] == 1 and t["finds"] == 1
    assert t["issues"][0] == {"x": "Sai ngày", "ref": "BB.pdf tr1", "nhan": "Lỗi hay gặp"}


def test_task_done_and_job_done():
    s = build_state(base() + [E("task_done", job="HS-0001", task="HS-0001.1", file="a.xlsx"),
                              E("job_done", job="HS-0001")])
    j = s["jobs"][0]
    assert j["status"] == "done" and j["tasks"][0]["status"] == "done" and j["tasks"][0]["pct"] == 100
    assert j["tasks"][0]["file"] == "a.xlsx" and s["agents"]["soat-cap-2"] == {"st": "idle", "task": None, "pct": 0, "done": 1}
    assert s["kpis"] == {"run": 0, "review": 0, "done": 1, "finds": 0}


def test_error_marks_job():
    s = build_state(base() + [E("error", job="HS-0001", reason="Không tìm thấy Claude Code trên máy")])
    assert s["jobs"][0]["status"] == "error" and s["jobs"][0]["error"] == "Không tìm thấy Claude Code trên máy"


def test_newest_job_first_and_feed():
    ev = base() + [E("job_created", job="HS-0002", title="Dot5", folder="D:/y", kind="tt", note="")]
    s = build_state(ev)
    assert [j["id"] for j in s["jobs"]] == ["HS-0002", "HS-0001"]
    assert s["feed"] and all({"t", "c", "x"} <= set(f) for f in s["feed"])


def test_progress_clamped_and_unknown_agent_ignored():
    ev = base() + [E("progress", job="HS-0001", task="HS-0001.1", pct=150),
                   E("task_assigned", job="HS-0001", task="HS-0001.9", agent="khong-co", desc="x")]
    s = build_state(ev)
    assert s["jobs"][0]["tasks"][0]["pct"] == 100 and "khong-co" not in s["agents"]
