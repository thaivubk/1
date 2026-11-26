"""Công cụ agent gọi qua: python -m vpak.tools <lệnh>."""
import os
from pathlib import Path

RESULT_DIR = "KetQua_Agent"


def ensure_result_path(path: Path) -> Path:
    """Chỉ cho ghi bên trong thư mục KetQua_Agent (của việc đang chạy nếu biết)."""
    p = Path(os.path.abspath(path))
    if ".." in Path(path).parts or RESULT_DIR not in p.parts:
        raise ValueError(f"Chỉ được ghi trong thư mục {RESULT_DIR}: {path}")
    folder = os.environ.get("VPAK_JOB_FOLDER")
    if folder:
        root = Path(os.path.abspath(folder)) / RESULT_DIR
        if p != root and root not in p.parents:
            raise ValueError(f"Chỉ được ghi trong {root}: {path}")
    return p
