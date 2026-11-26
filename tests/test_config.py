from vpak.config import load_config


def test_defaults(tmp_path):
    cfg = load_config(env={"VPAK_DATA": str(tmp_path / "d")}, repo_dir=tmp_path)
    assert cfg.port == 8765 and cfg.max_parallel == 2
    assert cfg.data_dir.is_dir()


def test_env_file_and_override(tmp_path):
    (tmp_path / ".env").write_text("TELEGRAM_CHAT_ID=111\n# chú thích\nVPAK_PORT=9000\n", encoding="utf-8")
    cfg = load_config(env={"VPAK_PORT": "9100", "VPAK_DATA": str(tmp_path / "d")}, repo_dir=tmp_path)
    assert cfg.telegram_chat_id == "111" and cfg.port == 9100


def test_claude_cmd_override(tmp_path):
    cfg = load_config(env={"VPAK_DATA": str(tmp_path / "d"), "VPAK_CLAUDE_CMD": "python fake.py"}, repo_dir=tmp_path)
    assert cfg.claude_cmd == ["python", "fake.py"]
