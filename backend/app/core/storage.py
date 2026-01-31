from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class TurnLog:
    t: str
    user: str
    prompt_sent: str
    answer: str
    rating: Optional[int] = None
    d_complexity: Optional[int] = None
    d_examples: Optional[int] = None
    d_structure: Optional[int] = None


@dataclass
class SessionState:
    session_id: str
    system_label: str           # A/B/C 只给用户看
    condition_sequence: List[str]  # 实际跑哪些条件（full/baseline/no_time/no_frequency）
    active_condition_index: int
    # SFUIM profile & counters
    profile: Dict[str, Any]
    turns: List[TurnLog]
    turn_count_by_condition: Dict[str, int]


class InMemoryStore:
    def __init__(self) -> None:
        self.sessions: Dict[str, SessionState] = {}

    def create_session(self, state: SessionState) -> None:
        self.sessions[state.session_id] = state

    def get(self, session_id: str) -> Optional[SessionState]:
        return self.sessions.get(session_id)
    

session_store = InMemoryStore()
