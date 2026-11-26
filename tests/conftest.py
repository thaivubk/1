import socket
import sys
import threading
import time
from pathlib import Path

import pytest

from vpak.config import load_config
from vpak.ledger import read_events

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def cfg(tmp_path):
    return load_config(env={"VPAK_DATA": str(tmp_path / "data")})


@pytest.fixture
def cfg_fake(tmp_path):
    return load_config(env={"VPAK_DATA": str(tmp_path / "data"),
                            "VPAK_CLAUDE_CMD": f'"{sys.executable}" "{REPO / "tests" / "fake_claude.py"}"'})


def wait_until(fn, timeout=15.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if fn():
            return True
        time.sleep(0.1)
    raise AssertionError("Hết thời gian chờ")


def events_of(cfg, job, typ):
    return [e for e in read_events(cfg.data_dir) if e.get("job") == job and e.get("type") == typ]


def make_folder(base: Path, name="Đợt 4") -> Path:
    f = base / "Công Việc" / "HĐ 125 Nhà trạm" / name
    f.mkdir(parents=True)
    (f / "To trình.pdf").write_bytes(b"%PDF-1.4")
    return f


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live(cfg_fake):
    import uvicorn

    from vpak.runner import JobRunner
    from vpak.server import create_app

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
