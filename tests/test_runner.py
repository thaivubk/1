import json
import os
from dataclasses import replace
from pathlib import Path

from conftest import events_of, make_folder, wait_until
from vpak.ledger import append_event, read_events
from vpak.runner import JobRunner, allowed_tools, build_prompt, guess_kind
from vpak.state import build_state


def run_to_end(r, cfg, job, n=1):
    wait_until(lambda: (r.pump(), len(events_of(cfg, job, "job_run_ended")) >= n)[1])


def test_submit_unicode_path(tmp_path, cfg):
    folder = make_folder(tmp_path)
    job = JobRunner(cfg).submit(str(folder))
    ev = events_of(cfg, job, "job_created")[-1]
    assert job == "HS-0001" and ev["title"] == "HĐ 125 Nhà trạm › Đợt 4" and ev["kind"] == "tt"
    assert ev["folder"] == str(folder)


def test_submit_missing_folder(cfg, tmp_path):
    import pytest
    with pytest.raises(ValueError, match="Không tìm thấy thư mục"):
        JobRunner(cfg).submit(str(tmp_path / "khong-co"))


def test_job_numbers_and_prefix(tmp_path, cfg):
    r = JobRunner(cfg)
    a = r.submit(str(make_folder(tmp_path, "A")))
    cd = tmp_path / "CongDoan" / "T11"; cd.mkdir(parents=True)
    b = r.submit(str(cd))
    assert (a, b) == ("HS-0001", "CD-0002")


def test_guess_kind():
    assert guess_kind(Path(r"D:\CongViec\CongDoan\2026\T11")) == "cd"
    assert guess_kind(Path(r"D:\CongViec\2026\QT_De-tai-KHCN")) == "qt"
    assert guess_kind(Path(r"D:\CongViec\VanBan\Moi")) == "qd"
    assert guess_kind(Path(r"D:\Công Việc\Quyết toán\DA1")) == "qt"
    assert guess_kind(Path(r"D:\CongViec\2026\HD-125\Dot4")) == "tt"


def test_allowed_tools_scope(tmp_path):
    folder = make_folder(tmp_path)
    tools = allowed_tools(str(folder))
    assert "Bash(python -m vpak.ghi_so:*)" in tools and "Task" in tools
    assert any(t.startswith("Write(") and "KetQua_Agent/**" in t for t in tools)
    assert not any(t in ("Write", "Edit", "Bash") for t in tools)


def test_run_with_fake_claude(tmp_path, cfg_fake):
    r = JobRunner(cfg_fake)
    job = r.submit(str(make_folder(tmp_path)))
    run_to_end(r, cfg_fake, job)
    ended = events_of(cfg_fake, job, "job_run_ended")[-1]
    assert ended["session_id"] == "fake-1" and ended["exit_code"] == 0
    assert events_of(cfg_fake, job, "job_done")  # tự đóng việc khi không còn câu hỏi
    assert (Path(events_of(cfg_fake, job, "job_created")[0]["folder"]) / "KetQua_Agent").is_dir()


def test_claude_missing(tmp_path, cfg):
    r = JobRunner(replace(cfg, claude_cmd=["khong-co-lenh-nay-vpak"]))
    job = r.submit(str(make_folder(tmp_path)))
    r.pump()
    assert events_of(cfg, job, "error")[-1]["reason"] == "Không tìm thấy Claude Code trên máy"
    assert build_state(read_events(cfg.data_dir))["jobs"][0]["status"] == "error"


def test_claude_fails(tmp_path, cfg_fake, monkeypatch):
    monkeypatch.setenv("FAKE_FAIL", "1")
    r = JobRunner(cfg_fake)
    job = r.submit(str(make_folder(tmp_path)))
    run_to_end(r, cfg_fake, job)
    reason = events_of(cfg_fake, job, "error")[-1]["reason"]
    assert reason.startswith("Claude Code báo lỗi:") and "Credit balance is too low" in reason
    assert build_state(read_events(cfg_fake.data_dir))["jobs"][0]["status"] == "error"


def test_max_parallel(tmp_path, cfg_fake, monkeypatch):
    monkeypatch.setenv("FAKE_SLEEP", "1.5")
    r = JobRunner(cfg_fake)
    jobs = [r.submit(str(make_folder(tmp_path, f"D{i}"))) for i in range(3)]
    r.pump()
    started = [e for e in read_events(cfg_fake.data_dir) if e["type"] == "job_started"]
    assert len(started) == 2
    wait_until(lambda: (r.pump(), all(events_of(cfg_fake, j, "job_run_ended") for j in jobs))[1])


def test_answer_resumes_session(tmp_path, cfg_fake, monkeypatch):
    monkeypatch.setenv("FAKE_ASK", "1")
    out = tmp_path / "env.json"
    r = JobRunner(cfg_fake)
    job = r.submit(str(make_folder(tmp_path)))
    run_to_end(r, cfg_fake, job)
    assert not events_of(cfg_fake, job, "job_done")
    qid = build_state(read_events(cfg_fake.data_dir))["questions"][0]["id"]
    monkeypatch.setenv("FAKE_ENV_OUT", str(out))
    r.answer(qid, "Có")
    run_to_end(r, cfg_fake, job, n=2)
    args = json.loads(out.read_text(encoding="utf-8"))["args"]
    assert args[args.index("--resume") + 1] == "fake-1"
    assert qid in args[args.index("-p") + 1] and "Có" in args[args.index("-p") + 1]


def test_answer_unknown_question(cfg):
    import pytest
    with pytest.raises(KeyError):
        JobRunner(cfg).answer("Q404", "x")


def test_env_has_no_api_key(tmp_path, cfg_fake, monkeypatch):
    out = tmp_path / "env.json"
    monkeypatch.setenv("FAKE_ENV_OUT", str(out))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    r = JobRunner(cfg_fake)
    job = r.submit(str(make_folder(tmp_path)))
    run_to_end(r, cfg_fake, job)
    env = json.loads(out.read_text(encoding="utf-8"))["env"]
    assert "ANTHROPIC_API_KEY" not in env and env["VPAK_JOB_ID"] == job and env["VPAK_DATA"] == str(cfg_fake.data_dir)


def test_recover_orphan(tmp_path, cfg):
    r = JobRunner(cfg)
    job = r.submit(str(make_folder(tmp_path)))
    append_event(cfg.data_dir, "job_started", job=job, pid=999999)
    (cfg.data_dir / "jobs").mkdir(exist_ok=True)
    (cfg.data_dir / "jobs" / f"{job}.pid").write_text("999999", encoding="utf-8")
    assert JobRunner(cfg).recover() == 1
    assert events_of(cfg, job, "error")[-1]["reason"] == "Mất kết nối khi server khởi động lại"
    assert JobRunner(cfg).recover() == 0


def test_build_prompt_fills_placeholders(cfg):
    p = build_prompt("HS-0001", r"D:\Đợt 4", "tt", "", r"D:\Đợt 4\KetQua_Agent\2026-11-25_HS-0001")
    assert "{job}" not in p and "HS-0001" in p and "KetQua_Agent" in p


def test_recover_requeues_unstarted(tmp_path, cfg_fake):
    job = JobRunner(cfg_fake).submit(str(make_folder(tmp_path)))
    r = JobRunner(cfg_fake)
    assert r.recover() == 1
    run_to_end(r, cfg_fake, job)
    assert events_of(cfg_fake, job, "job_done")
