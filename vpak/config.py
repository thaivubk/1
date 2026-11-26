"""Đọc cấu hình từ biến môi trường và file .env ở gốc repo."""
from __future__ import annotations

import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

REPO_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    repo_dir: Path
    data_dir: Path
    port: int
    max_parallel: int
    telegram_token: str
    telegram_chat_id: str
    lookup_url: str
    claude_cmd: list[str]


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config(env: Mapping[str, str] | None = None, repo_dir: Path | None = None) -> Config:
    repo = Path(repo_dir) if repo_dir else REPO_DIR
    merged = _read_env_file(repo / ".env")
    merged.update(os.environ if env is None else env)
    data_dir = Path(merged.get("VPAK_DATA") or Path.home() / "VanPhongAgent_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    cmd = merged.get("VPAK_CLAUDE_CMD")
    claude_cmd = shlex.split(cmd) if cmd else [shutil.which("claude") or "claude"]
    return Config(
        repo_dir=repo,
        data_dir=data_dir,
        port=int(merged.get("VPAK_PORT") or 8765),
        max_parallel=int(merged.get("VPAK_MAX_PARALLEL") or 2),
        telegram_token=merged.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=merged.get("TELEGRAM_CHAT_ID", ""),
        lookup_url=merged.get("VPAK_LOOKUP_URL", ""),
        claude_cmd=claude_cmd,
    )
