import json
import time

from vpak import statusline
from vpak.server import read_quota


def test_statusline_saves_quota(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    payload = {"model": {"display_name": "Opus"}, "rate_limits": {
        "five_hour": {"used_percentage": 42.5, "resets_at": 1800000000},
        "seven_day": {"used_percentage": 88, "resets_at": 1800300000}}}
    assert statusline.main(json.dumps(payload)) == 0
    q = read_quota(tmp_path)
    assert q["five_hour"]["used_percentage"] == 42.5 and q["seven_day"]["used_percentage"] == 88
    assert "5 giờ 43%" in capsys.readouterr().out


def test_statusline_without_limits_keeps_old(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    statusline.main(json.dumps({"rate_limits": {"five_hour": {"used_percentage": 10, "resets_at": 1}}}))
    statusline.main(json.dumps({"model": {}}))
    assert read_quota(tmp_path)["five_hour"]["used_percentage"] == 10


def test_statusline_bad_input_never_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    assert statusline.main("không phải json") == 0


def test_read_quota_missing_or_stale(tmp_path):
    assert read_quota(tmp_path) is None
    (tmp_path / "quota.json").write_text(json.dumps({"five_hour": {"used_percentage": 1, "resets_at": 1}, "at": time.time() - 8 * 86400}), encoding="utf-8")
    assert read_quota(tmp_path) is None


def test_settings_registers_statusline():
    from pathlib import Path
    s = json.loads(Path(".claude/settings.json").read_text(encoding="utf-8"))
    assert s["statusLine"]["command"] == "python -m vpak.statusline"
