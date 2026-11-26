from vpak.config import load_config
from vpak.ledger import append_event, read_events
from vpak.notifier import Notifier
from vpak.telegram import send_message


def make(tmp_path):
    sent = []
    n = Notifier(tmp_path, lambda t: sent.append(t) or True)
    n.poll()
    return n, sent


def test_done_message(tmp_path):
    n, sent = make(tmp_path)
    append_event(tmp_path, "finding", job="HS-0001", task="t", agent="soat-cap-1", text="x", nguon="y")
    append_event(tmp_path, "job_done", job="HS-0001")
    assert n.poll() == 1 and sent == ["Xong HS-0001: 1 phát hiện, kết quả đã lưu."]
    assert read_events(tmp_path)[-1]["type"] == "notify"


def test_waiting_message(tmp_path):
    n, sent = make(tmp_path)
    append_event(tmp_path, "question", job="HS-0001", task="t", agent="soat-cap-2", qid="Q1", q="?", choices=["a", "b"])
    append_event(tmp_path, "job_run_ended", job="HS-0001", exit_code=0, session_id="s")
    assert n.poll() == 1 and sent == ["HS-0001 chờ đại ca quyết 1 câu."]


def test_answered_question_not_counted(tmp_path):
    n, sent = make(tmp_path)
    append_event(tmp_path, "question", job="HS-0001", task="t", agent="soat-cap-2", qid="Q1", q="?", choices=["a", "b"])
    append_event(tmp_path, "decision", job="HS-0001", qid="Q1", answer="a")
    append_event(tmp_path, "job_run_ended", job="HS-0001", exit_code=0, session_id="s")
    assert n.poll() == 0 and sent == []


def test_error_message_truncated(tmp_path):
    n, sent = make(tmp_path)
    append_event(tmp_path, "error", job="HS-0001", reason="x" * 300)
    n.poll()
    assert sent[0].startswith("HS-0001 gặp lỗi: ") and len(sent[0]) == len("HS-0001 gặp lỗi: ") + 120


def test_first_run_does_not_resend_history(tmp_path):
    append_event(tmp_path, "job_done", job="HS-0001")
    sent = []
    assert Notifier(tmp_path, lambda t: sent.append(t) or True).poll() == 0 and sent == []


def test_no_resend_after_restart(tmp_path):
    n, sent = make(tmp_path)
    append_event(tmp_path, "job_done", job="HS-0001")
    n.poll()
    again = []
    assert Notifier(tmp_path, lambda t: again.append(t) or True).poll() == 0 and again == []


def test_send_message_without_token_returns_false(tmp_path):
    cfg = load_config(env={"VPAK_DATA": str(tmp_path)}, repo_dir=tmp_path)
    assert send_message(cfg, "chào") is False
