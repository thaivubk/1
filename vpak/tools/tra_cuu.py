"""Tra cứu văn bản qua web app của đại ca. Lỗi hoặc rỗng → None (agent chuyển sang tra Internet)."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from ..config import Config


def lookup(cfg: Config, so_hieu: str) -> dict | None:
    if not cfg.lookup_url:
        return None
    param = os.environ.get("VPAK_LOOKUP_PARAM", "q")
    sep = "&" if "?" in cfg.lookup_url else "?"
    url = f"{cfg.lookup_url}{sep}{urllib.parse.urlencode({param: so_hieu})}"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    if isinstance(data, list):
        data = {"ket_qua": data} if data else None
    return data or None
