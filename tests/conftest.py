import sys
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
