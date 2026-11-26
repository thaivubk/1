import glob
import socket
import threading
import time

import pytest

pytest.importorskip("playwright")
import uvicorn  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from conftest import events_of, make_folder, wait_until  # noqa: E402
from vpak.ledger import append_event  # noqa: E402
from vpak.runner import JobRunner  # noqa: E402
from vpak.server import create_app  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live(cfg_fake):
    port = _free_port()
    runner = JobRunner(cfg_fake)
    app = create_app(cfg_fake, runner, background=True, opener=lambda p: None, browse=lambda: None)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    wait_until(lambda: server.started)
    yield f"http://127.0.0.1:{port}", runner, cfg_fake
    server.should_exit = True
    t.join(5)


@pytest.fixture
def page():
    exe = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")
    args = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe[0], args=args) if exe else p.chromium.launch(args=args)
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        yield pg
        b.close()


def test_page_loads_and_shows_agents(live, page):
    page.goto(live[0] + "/")
    page.wait_for_function("document.querySelectorAll('.lbl').length === 13", timeout=15000)
    assert page.errors == []
    assert "Chưa có số liệu" in page.text_content(".topbar")


def test_submit_bad_folder_shows_message(live, page):
    page.goto(live[0] + "/")
    page.wait_for_selector(".lbl")
    page.fill("#folder", "Z:/khong/co")
    page.click("button.go")
    page.wait_for_function("document.querySelector('#cmdMsg').textContent.includes('Không tìm thấy thư mục')")


def test_new_job_appears_in_ledger(live, page, tmp_path):
    page.goto(live[0] + "/")
    page.wait_for_selector(".lbl")
    page.fill("#folder", str(make_folder(tmp_path)))
    page.click("button.go")
    page.wait_for_function("document.querySelector('#tbody').textContent.includes('HS-0001')", timeout=15000)
    assert page.errors == []


def test_answer_question_from_page(live, page, tmp_path):
    url, runner, cfg = live
    job = runner.submit(str(make_folder(tmp_path)))
    append_event(cfg.data_dir, "task_assigned", job=job, task=job + ".1", agent="soat-cap-2", desc="Soát cấp 2")
    append_event(cfg.data_dir, "question", job=job, task=job + ".1", agent="soat-cap-2", qid="QW1",
                 q="Chấp nhận bản scan?", choices=["Chấp nhận", "Yêu cầu bản gốc"])
    page.goto(url + "/")
    page.click("button[data-q='QW1'][data-i='0']", timeout=15000)
    wait_until(lambda: events_of(cfg, job, "decision"))
    assert events_of(cfg, job, "decision")[-1]["answer"] == "Chấp nhận"


def test_map_view(live, page):
    page.goto(live[0] + "/")
    page.wait_for_selector(".lbl")
    page.click("#segMap")
    page.wait_for_function("document.querySelectorAll('.mcard').length === 12")
    assert page.errors == []
