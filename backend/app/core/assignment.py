import json
import os
import random
import threading
from typing import Dict

# 这个路径最好用“绝对定位 backend/data”，跟你 persistence 的做法一致
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # -> backend/
DATA_DIR = os.path.join(BASE_DIR, "data")


_lock = threading.Lock()


LATIN_SQUARE_SEQUENCES = {
    "A": ["full", "baseline", "no_time", "no_frequency"],
    "B": ["baseline", "no_time", "no_frequency", "full"],
    "C": ["no_time", "no_frequency", "full", "baseline"],
    "D": ["no_frequency", "full", "baseline", "no_time"],
}

def _read_counts(path: str) -> Dict[str, int]:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(path):
        return {"A": 0, "B": 0, "C": 0, "D": 0}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for k in ["A", "B", "C", "D"]:
        data.setdefault(k, 0)

    return {k: int(data[k]) for k in ["A", "B", "C", "D"]}



def _atomic_write_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # Windows 下也可用，原子替换


def assign_system_label_balanced(dev_mode: bool = False) -> str:
    with _lock:
        path = _get_counts_path(dev_mode)
        counts = _read_counts(path)

        min_count = min(counts.values())
        candidates = [k for k, v in counts.items() if v == min_count]
        label = random.choice(candidates)

        counts[label] += 1
        _atomic_write_json(path, counts)

        return label

def get_condition_sequence_for_label(label: str) -> list[str]:
    return LATIN_SQUARE_SEQUENCES[label]

def get_label_counts(dev_mode: bool = False) -> Dict[str, int]:
    with _lock:
        path = _get_counts_path(dev_mode)
        return _read_counts(path)


def _get_counts_path(dev_mode: bool) -> str:
    filename = "label_counts_dev.json" if dev_mode else "label_counts.json"
    return os.path.join(DATA_DIR, filename)
