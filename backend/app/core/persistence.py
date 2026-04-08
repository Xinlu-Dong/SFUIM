import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

from app.core.sfuim_engine import normalize_profile, SFUIMConfig
from app.core.storage import SessionState, TurnLog, InMemoryStore


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_ROOT = os.path.join(BASE_DIR, "data")


def get_sessions_dir(namespace: str) -> str:
    if namespace in ("pilot", "pilot_legacy"):
        return os.path.join(DATA_ROOT, "sessions_pilot")
    return os.path.join(DATA_ROOT, "sessions_final")


def _json_safe(obj: Any):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def save_session(state: SessionState) -> None:
    data_dir = get_sessions_dir(state.assignment_namespace)
    os.makedirs(data_dir, exist_ok=True)

    path = os.path.join(data_dir, f"{state.session_id}.json")
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
    return normalize_profile(profile, SFUIMConfig())


def load_session(session_id: str, namespace: str) -> Optional[SessionState]:
    data_dir = get_sessions_dir(namespace)
    path = os.path.join(data_dir, f"{session_id}.json")
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
        study_phase=data.get("study_phase", "pilot_legacy"),
        engine_version=data.get("engine_version", "legacy_unknown"),
        config_snapshot=data.get("config_snapshot", {}),
        assignment_namespace=data.get("assignment_namespace", namespace),
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
    for namespace in ("pilot", "final"):
        data_dir = get_sessions_dir(namespace)
        if not os.path.exists(data_dir):
            continue

        for filename in os.listdir(data_dir):
            if not filename.endswith(".json"):
                continue

            session_id = filename.replace(".json", "")

            try:
                state = load_session(session_id, namespace=namespace)
                if state:
                    session_store.create_session(state)
            except Exception as e:
                print(f"[restore_all_sessions] Skip {namespace}/{filename}: {e}")