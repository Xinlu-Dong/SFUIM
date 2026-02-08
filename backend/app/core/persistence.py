import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.core.storage import SessionState


DATA_DIR = "backend/data/sessions"


def _json_safe(obj: Any):
    """
    处理 JSON 不支持的类型（如 datetime）
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def save_session(state: SessionState) -> None:
    """
    将整个 SessionState 覆盖写入一个 JSON 文件
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    path = os.path.join(DATA_DIR, f"{state.session_id}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            asdict(state),
            f,
            ensure_ascii=False,
            indent=2,
            default=_json_safe,
        )
