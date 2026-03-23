import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.core.sfuim_engine import normalize_profile, SFUIMConfig
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
    将整个 SessionState 原子写入一个 JSON 文件。
    先写临时文件，再用 os.replace 覆盖正式文件，降低文件损坏风险。
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{state.session_id}.json")
    tmp_path = f"{path}.tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(
            asdict(state),
            f,
            ensure_ascii=False,
            indent=2,
            default=_json_safe,
        )

    os.replace(tmp_path, path)


def _normalize_profile(profile: dict) -> dict:
    """
    复用新版 sfuim_engine 中的 normalize_profile，
    统一兼容新版 profile 与旧版 profile。
    """
    return normalize_profile(profile, SFUIMConfig())


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
        topic_sequence=topic_sequence,
        profiles_by_condition=profiles_by_condition,
        turns=turns,
        turn_count_by_condition=data["turn_count_by_condition"],
        ended_reason_by_condition=data["ended_reason_by_condition"],
        post_study=data.get("post_study"),
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