import json
import os
import random
import threading
from typing import Dict, List

from app.core.topic_catalog import get_topic_catalog, TopicItem

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # -> backend/
DATA_DIR = os.path.join(BASE_DIR, "data")
_lock = threading.Lock()

# 4-topic balanced rotation / Latin-style orders
TOPIC_ORDER_MAP = {
    "A": [0, 1, 2, 3],
    "B": [1, 2, 3, 0],
    "C": [2, 3, 0, 1],
    "D": [3, 0, 1, 2],
}


def _counts_path(dev_mode: bool = False) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = "topic_counts.dev.json" if dev_mode else "topic_counts.json"
    return os.path.join(DATA_DIR, filename)


def _read_counts(path: str) -> Dict[str, int]:
    if not os.path.exists(path):
        return {"A": 0, "B": 0, "C": 0, "D": 0}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for k in ["A", "B", "C", "D"]:
        data.setdefault(k, 0)

    return {k: int(data[k]) for k in ["A", "B", "C", "D"]}


def _write_counts(path: str, counts: Dict[str, int]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(counts, f, ensure_ascii=False, indent=2)


def get_topic_label_counts(dev_mode: bool = False) -> Dict[str, int]:
    path = _counts_path(dev_mode=dev_mode)
    with _lock:
        return _read_counts(path)


def assign_topic_label_balanced(dev_mode: bool = False) -> str:
    """
    Assign one of A/B/C/D with minimum-count balancing.
    If several labels are tied for the minimum count, randomly choose one of them.
    """
    path = _counts_path(dev_mode=dev_mode)

    with _lock:
        counts = _read_counts(path)
        min_count = min(counts.values())
        candidates = [label for label, c in counts.items() if c == min_count]
        chosen = random.choice(candidates)
        counts[chosen] += 1
        _write_counts(path, counts)
        return chosen


def get_topic_sequence_for_label(label: str) -> List[TopicItem]:
    if label not in TOPIC_ORDER_MAP:
        raise ValueError(f"Unknown topic order label: {label}")

    catalog = get_topic_catalog()
    if len(catalog) != 4:
        raise ValueError(
            f"Expected exactly 4 topics in TOPIC_CATALOG, got {len(catalog)}"
        )

    order = TOPIC_ORDER_MAP[label]
    return [catalog[i] for i in order]


def build_topic_sequence(topic_order_label: str) -> List[TopicItem]:
    return get_topic_sequence_for_label(topic_order_label)