import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any
import copy
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

def _migrate_profile(data: dict) -> dict:
    # 兼容旧版：只有 profile，没有 profiles_by_condition
    if "profiles_by_condition" in data:
        return data["profiles_by_condition"]
    if "profile" in data:
        # 把旧的共享 profile “复制”给每个 condition（或只给当前 active）
        seq = data.get("condition_sequence", [])
        return {c: copy.deepcopy(data["profile"]) for c in seq}
    # 最坏情况：没有任何 profile 字段
    return {}

def load_session(session_id: str) -> SessionState | None:
    """
    从 JSON 文件读取 SessionState
    """
    path = os.path.join(DATA_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 恢复 TurnLog 列表
    turns = [TurnLog(**t) for t in data.get("turns", [])]

    state = SessionState(
        session_id=data["session_id"],
        system_label=data["system_label"],
        condition_sequence=data["condition_sequence"],
        active_condition_index=data["active_condition_index"],
        profiles_by_condition=_migrate_profile(data),
        turns=turns,
        turn_count_by_condition=data["turn_count_by_condition"],
        ended_reason_by_condition=data["ended_reason_by_condition"],
    )

    return state


def restore_all_sessions(session_store: InMemoryStore) -> None:
    """
    启动时扫描 sessions 目录，恢复所有 session 到内存
    """
    if not os.path.exists(DATA_DIR):
        return

    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".json"):
            continue

        session_id = filename.replace(".json", "")
        state = load_session(session_id)
        if state:
            session_store.create_session(state)

