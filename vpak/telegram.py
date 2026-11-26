"""Gửi tin Telegram qua Bot API. Không bao giờ ném lỗi."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .config import Config


def send_message(cfg: Config, text: str) -> bool:
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        return False
    url = f"https://api.telegram.org/bot{cfg.telegram_token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": cfg.telegram_chat_id, "text": text}).encode("utf-8")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=10) as r:
            return bool(json.loads(r.read().decode("utf-8")).get("ok"))
    except Exception:
        return False
