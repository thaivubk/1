import json

from vpak import hook
from vpak.ledger import read_events


def test_hook_start_stop(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    monkeypatch.setenv("VPAK_JOB_ID", "HS-0001")
    for name in ("SubagentStart", "SubagentStop"):
        assert hook.main(json.dumps({"hook_event_name": name, "agent_type": "soat-cap-1",
                                     "agent_id": "a1", "session_id": "s1"})) == 0
    evs = read_events(tmp_path)
    assert [e["type"] for e in evs] == ["agent_started", "agent_stopped"]
    assert evs[0]["agent"] == "soat-cap-1" and evs[0]["job"] == "HS-0001" and evs[0]["session_id"] == "s1"


def test_hook_bad_json_never_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    assert hook.main("{không phải json") == 0
    assert (tmp_path / "hook-errors.log").exists()


def test_hook_other_event_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("VPAK_DATA", str(tmp_path))
    assert hook.main(json.dumps({"hook_event_name": "PreToolUse"})) == 0
    assert read_events(tmp_path) == []


def test_settings_registers_hooks():
    from pathlib import Path
    s = json.loads(Path(".claude/settings.json").read_text(encoding="utf-8"))
    for name in ("SubagentStart", "SubagentStop"):
        assert s["hooks"][name][0]["hooks"][0]["command"] == "python -m vpak.hook"
