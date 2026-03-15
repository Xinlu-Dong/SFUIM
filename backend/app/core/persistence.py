import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.core.storage import SessionState, TurnLog, InMemoryStore


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "sessions")


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


def _normalize_profile(profile: dict) -> dict:
    """
    将 profile 规范化为当前 SFUIM 正式结构：
    {
        "theta": {"C": float, "E": float, "S": float},
        "s": float,
        "last_k": {"C": int, "E": int, "S": int},
        "count": {"C": int, "E": int, "S": int},
        "k": int
    }
    """
    if not isinstance(profile, dict):
        profile = {}

    theta = profile.get("theta", {})
    last_k = profile.get("last_k", {})
    count = profile.get("count", {})

    return {
        "theta": {
            "C": float(theta.get("C", 0.0)),
            "E": float(theta.get("E", 0.0)),
            "S": float(theta.get("S", 0.0)),
        },
        "s": float(profile.get("s", 0.5)),
        "last_k": {
            "C": int(last_k.get("C", 0)),
            "E": int(last_k.get("E", 0)),
            "S": int(last_k.get("S", 0)),
        },
        "count": {
            "C": int(count.get("C", 0)),
            "E": int(count.get("E", 0)),
            "S": int(count.get("S", 0)),
        },
        "k": int(profile.get("k", 0)),
    }


def load_session(session_id: str) -> SessionState | None:
    """
    从 JSON 文件读取 SessionState。
    只支持当前正式版本的 session 结构：
    必须包含 profiles_by_condition。
    """
    path = os.path.join(DATA_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "profiles_by_condition" not in data:
        raise ValueError(
            f"Session {session_id} is in an old unsupported format: missing 'profiles_by_condition'."
        )

    seq = data["condition_sequence"]
    topic_order_label = data.get("topic_order_label", "A")
    topic_sequence = data.get("topic_sequence", [])
    raw_profiles = data["profiles_by_condition"]

    profiles_by_condition = {
        c: _normalize_profile(raw_profiles.get(c, {}))
        for c in seq
    }

    turns = [TurnLog(**t) for t in data.get("turns", [])]

    state = SessionState(
        session_id=data["session_id"],
        system_label=data["system_label"],
        condition_sequence=seq,
        active_condition_index=data["active_condition_index"],
        profiles_by_condition=profiles_by_condition,
        turns=turns,
        turn_count_by_condition=data["turn_count_by_condition"],
        ended_reason_by_condition=data["ended_reason_by_condition"],
        topic_order_label=topic_order_label,
        topic_sequence=topic_sequence,
    )

    return state


def restore_all_sessions(session_store: InMemoryStore) -> None:
    """
    启动时扫描 sessions 目录，恢复所有当前版本 session 到内存。
    如果遇到旧版本或损坏文件，则跳过并打印提示。
    """
    if not os.path.exists(DATA_DIR):
        return

    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".json"):
            continue

        session_id = filename.replace(".json", "")

        try:
            state = load_session(session_id)
            if state:
                session_store.create_session(state)
        except Exception as e:
            print(f"[restore_all_sessions] Skip {filename}: {e}")