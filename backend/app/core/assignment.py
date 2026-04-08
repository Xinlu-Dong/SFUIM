import json
import os
import threading
from typing import Dict, List, TypedDict

from app.core.topic_catalog import get_topic_catalog, TopicItem

# 绝对定位到 backend/data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # -> backend/
DATA_DIR = os.path.join(BASE_DIR, "data")

_lock = threading.Lock()

LABEL_ORDER = ["A", "B", "C", "D"]

LATIN_SQUARE_SEQUENCES = {
    "A": ["full", "baseline", "no_time", "no_frequency"],
    "B": ["baseline", "no_time", "no_frequency", "full"],
    "C": ["no_time", "no_frequency", "full", "baseline"],
    "D": ["no_frequency", "full", "baseline", "no_time"],
}


class AssignmentState(TypedDict):
    next_index: int
    counts: Dict[str, int]


def _normalize_namespace(namespace: str) -> str:
    """
    统一 namespace 命名，避免传入空值或奇怪字符串。
    你现在正式实验就传 "final"，pilot 传 "pilot"。
    """
    ns = (namespace or "").strip().lower()
    if not ns:
        return "final"
    return ns


def _get_state_path(dev_mode: bool, namespace: str = "final") -> str:
    """
    为不同实验批次生成不同 assignment state 文件：

    正式实验:
      assignment_state_final.json
    pilot:
      assignment_state_pilot.json

    dev 模式:
      assignment_state_dev_final.json
      assignment_state_dev_pilot.json
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    ns = _normalize_namespace(namespace)

    if dev_mode:
        filename = f"assignment_state_dev_{ns}.json"
    else:
        filename = f"assignment_state_{ns}.json"

    return os.path.join(DATA_DIR, filename)


def _default_state() -> AssignmentState:
    return {
        "next_index": 0,
        "counts": {label: 0 for label in LABEL_ORDER},
    }


def _read_state(path: str) -> AssignmentState:
    if not os.path.exists(path):
        return _default_state()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    next_index = int(data.get("next_index", 0)) % len(LABEL_ORDER)

    raw_counts = data.get("counts", {})
    counts = {label: int(raw_counts.get(label, 0)) for label in LABEL_ORDER}

    return {
        "next_index": next_index,
        "counts": counts,
    }


def _atomic_write_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def assign_system_label_round_robin(dev_mode: bool = False, namespace: str = "final") -> str:
    """
    严格循环分配标签：
    A -> B -> C -> D -> A -> ...

    关键改动：
    现在每个 namespace（例如 pilot / final）都有自己独立的 assignment state。
    """
    with _lock:
        path = _get_state_path(dev_mode=dev_mode, namespace=namespace)
        state = _read_state(path)

        idx = state["next_index"]
        label = LABEL_ORDER[idx]

        state["counts"][label] += 1
        state["next_index"] = (idx + 1) % len(LABEL_ORDER)

        _atomic_write_json(path, state)
        return label


def get_condition_sequence_for_label(label: str) -> List[str]:
    if label not in LATIN_SQUARE_SEQUENCES:
        raise ValueError(f"Unknown system label: {label}")
    return list(LATIN_SQUARE_SEQUENCES[label])


def get_fixed_topic_sequence() -> List[TopicItem]:
    """
    Fixed topic order for every participant:
    topic0 -> topic1 -> topic2 -> topic3
    """
    catalog = get_topic_catalog()
    if len(catalog) != 4:
        raise ValueError(f"Expected exactly 4 topics in TOPIC_CATALOG, got {len(catalog)}")
    return catalog


def build_assignment_for_label(label: str) -> List[dict]:
    """
    Pair a Latin-square system order with the fixed topic order.

    Example:
    [
        {"condition": "full", "topic": topic0},
        {"condition": "baseline", "topic": topic1},
        {"condition": "no_time", "topic": topic2},
        {"condition": "no_frequency", "topic": topic3},
    ]
    """
    conditions = get_condition_sequence_for_label(label)
    topics = get_fixed_topic_sequence()

    if len(conditions) != len(topics):
        raise ValueError(
            f"Condition/topic length mismatch: {len(conditions)} vs {len(topics)}"
        )

    return [
        {"condition": cond, "topic": topic}
        for cond, topic in zip(conditions, topics)
    ]


def get_assignment_state(dev_mode: bool = False, namespace: str = "final") -> AssignmentState:
    with _lock:
        path = _get_state_path(dev_mode=dev_mode, namespace=namespace)
        return _read_state(path)


def get_label_counts(dev_mode: bool = False, namespace: str = "final") -> Dict[str, int]:
    with _lock:
        path = _get_state_path(dev_mode=dev_mode, namespace=namespace)
        return _read_state(path)["counts"]