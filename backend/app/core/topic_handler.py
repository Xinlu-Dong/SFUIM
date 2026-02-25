import re
from typing import Dict, Optional, Set, Tuple

# 轻量停用词：够用就行，后面可扩展
_STOPWORDS_ZH = {
    "我","你","他","她","它","我们","你们","他们",
    "什么","怎么","为什么","如何","能否","是否",
    "这个","那个","以及","还有","如果","因为","所以",
    "一个","一些","很多","非常","比较","这样","那样",
}

def tokenize_simple(text: str) -> Set[str]:
    """
    超轻量 tokeniser：
    - 英文/数字按连续块
    - 中文按连续2个以上字符块（避免单字噪声）
    """
    chunks = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", text)
    toks = set()
    for c in chunks:
        c = c.lower().strip()
        if len(c) < 2:
            continue
        if c in _STOPWORDS_ZH:
            continue
        toks.add(c)
    return toks

def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def detect_new_topic(
    user_msg: str,
    current_task: Optional[str],
    *,
    jaccard_threshold: float = 0.25,
) -> Tuple[bool, Dict]:
    """
    NewTopic 判别：
    - task 空 => True
    - Jaccard 相似度 < threshold => True
    """
    task = (current_task or "").strip()
    user = (user_msg or "").strip()

    user_toks = tokenize_simple(user)
    task_toks = tokenize_simple(task)

    if not task:
        return True, {"reason": "empty_task", "sim": None, "user_toks": list(user_toks), "task_toks": list(task_toks)}

    sim = jaccard(user_toks, task_toks)
    is_new = sim < jaccard_threshold

    return is_new, {
        "reason": "jaccard",
        "sim": sim,
        "threshold": jaccard_threshold,
        "user_toks": list(user_toks),
        "task_toks": list(task_toks),
    }

def update_task_state(
    profile: Dict,
    user_msg: str,
    *,
    jaccard_threshold: float = 0.25,
    keep_history: bool = True,
) -> Tuple[Dict, Dict]:
    """
    更新 profile["task"]，并返回 debug_info（用于日志）。
    """
    task_before = profile.get("task", "")
    is_new, det_dbg = detect_new_topic(user_msg, task_before, jaccard_threshold=jaccard_threshold)

    if is_new:
        profile["task"] = user_msg

    if keep_history:
        profile.setdefault("task_history", []).append(profile.get("task", ""))

    debug = {
        "task_before": task_before,
        "task_after": profile.get("task", ""),
        "user_msg": user_msg,
        "new_topic": is_new,
        "detector": det_dbg,
    }
    return profile, debug
