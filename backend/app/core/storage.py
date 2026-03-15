from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from typing import Literal

Condition = Literal["full", "baseline", "no_time", "no_frequency"]


@dataclass
class TurnLog:
    t: str
    condition: Condition
    user: str
    prompt_sent: str
    answer: str
    
    rating: Optional[int] = None                # overall rating in [-5, 5]
    d_complexity: Optional[float] = None        # continuous feedback in [-1, 1]
    d_examples: Optional[float] = None          # continuous feedback in [-1, 1]
    d_structure: Optional[float] = None         # continuous feedback in [-1, 1]
   
    # topic info for later analysis
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None

@dataclass
class SessionState:
    session_id: str
    system_label: str           # A/B/C/D 是4种顺序组标签，表示参与者被分配到那一组系统顺序
    condition_sequence: List[Condition]  # 实际跑哪些条件（full/baseline/no_time/ no_frequency）
    active_condition_index: int
    
    # independent topic-order assignment
    topic_order_label: str
    topic_sequence: List[Dict[str, str]]
    
    profiles_by_condition: Dict[Condition, Dict[str, Any]] # each profile stores theta, s, last_k, count, k
    turns: List[TurnLog]
    turn_count_by_condition: Dict[Condition, int]#最多10轮对话
    ended_reason_by_condition: Dict[Condition, Optional[str]]#每个系统结束的原因：10轮已满 or 提前结束
    
    


class InMemoryStore:
    def __init__(self) -> None:
        self.sessions: Dict[str, SessionState] = {}

    def create_session(self, state: SessionState) -> None:
        self.sessions[state.session_id] = state

    def get(self, session_id: str) -> Optional[SessionState]:
        return self.sessions.get(session_id)
    

session_store = InMemoryStore()
