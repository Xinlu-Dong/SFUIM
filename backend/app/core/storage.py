from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class TurnLog:
    t: str
    condition: str
    user: str
    prompt_sent: str
    answer: str
    rating: Optional[int] = None
    d_complexity: Optional[int] = None
    d_examples: Optional[int] = None
    d_structure: Optional[int] = None

    # ✅ topic debug（detect_only）
    topic_mode : Optional[str] = None # "off" | "detect" | "update"
    topic_ref: Optional[str] = None         # reference used for drift detection (e.g., previous user msg)
    topic_drift: Optional[bool] = None        # 是否疑似换题
    topic_sim: Optional[float] = None         # jaccard 相似度（可能为 None）
    topic_threshold: Optional[float] = None   # 阈值
    topic_reason: Optional[str] = None        # "empty_task" / "jaccard"


@dataclass
class SessionState:
    session_id: str
    system_label: str           # A/B/C 只给用户看
    condition_sequence: List[str]  # 实际跑哪些条件（full/baseline/no_time or no_frequency）
    active_condition_index: int
    # SFUIM profile & counters
    #profile: Dict[str, Any] 为了避免不同系统共用同一个Profile，把这个改成下面一行：
    profiles_by_condition: Dict[str, Dict[str, Any]] #每个 condition 一个 profile
    turns: List[TurnLog]
    turn_count_by_condition: Dict[str, int]#最多10轮对话
    ended_reason_by_condition: Dict[str, Optional[str]]#用户结束对话原因
    topic_mode: str = "detect"  # "off" | "detect" | "update"



class InMemoryStore:
    def __init__(self) -> None:
        self.sessions: Dict[str, SessionState] = {}

    def create_session(self, state: SessionState) -> None:
        self.sessions[state.session_id] = state

    def get(self, session_id: str) -> Optional[SessionState]:
        return self.sessions.get(session_id)
    

session_store = InMemoryStore()
