from dataclasses import replace

from vpak import kiem_tra
from vpak.kiem_tra import checks


def as_dict(cfg, env):
    return {name: (ok, note, req) for name, ok, note, req in checks(cfg, env)}


def test_api_key_flagged(cfg):
    res = as_dict(cfg, {"ANTHROPIC_API_KEY": "sk-x"})
    assert res["Không dùng API key"][0] is False and "Gỡ biến" in res["Không dùng API key"][1]
    assert as_dict(cfg, {})["Không dùng API key"][0] is True


def test_missing_env_keys(cfg):
    res = as_dict(replace(cfg, telegram_token="", telegram_chat_id="1", lookup_url=""), {})
    ok, note, _ = res[".env đủ khóa"]
    assert ok is False and "TELEGRAM_BOT_TOKEN" in note and "VPAK_LOOKUP_URL" in note


def test_python_version_and_packages_ok(cfg):
    res = as_dict(cfg, {})
    assert res["Python ≥ 3.10"][0] and res["Gói Python"][0] and res["Thư mục dữ liệu"][0]


def test_claude_missing_is_required_failure(cfg, capsys):
    res = as_dict(replace(cfg, claude_cmd=["khong-co-claude-vpak"]), {})
    assert res["Claude Code"][0] is False and res["Claude Code"][2] is True


def test_main_returns_1_when_required_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    monkeypatch.setenv("VPAK_CLAUDE_CMD", "khong-co-claude-vpak")
    assert kiem_tra.main([]) == 1
    assert "✘" in capsys.readouterr().out
