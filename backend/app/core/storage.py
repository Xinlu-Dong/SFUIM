from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TypedDict, Literal


Condition = Literal["full", "baseline", "no_time", "no_frequency"]


class TopicItem(TypedDict):
    id: str
    title: str


@dataclass
class TurnLog:
    t: str
    condition: Condition
    user: str
    prompt_sent: str
    answer: str

    # overall feedback for this turn
    rating: Optional[int] = None                # overall rating in [-5, 5]
    d_complexity: Optional[float] = None        # continuous feedback in [-1, 1]
    d_examples: Optional[float] = None          # continuous feedback in [-1, 1]
    d_structure: Optional[float] = None         # continuous feedback in [-1, 1]

    # topic info for later analysis
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None

    # follow-up / grounding info
    is_followup_detected: bool = False
    rewritten_user_message: Optional[str] = None
    topic_title_used: Optional[str] = None
    recent_user_context_used: List[str] = field(default_factory=list)


    # optional profile snapshots for analysis/debugging
    # profile used to render the current answer
    profile_used_q: Optional[Dict[str, int]] = None
    profile_used_theta: Optional[Dict[str, float]] = None
    profile_used_z: Optional[Dict[str, float]] = None
    profile_used_s: Optional[float] = None
    
    # profile after this turn's feedback update
    profile_after_feedback_q: Optional[Dict[str, int]] = None
    profile_after_feedback_theta: Optional[Dict[str, float]] = None
    profile_after_feedback_s: Optional[float] = None
    profile_after_feedback_z: Optional[Dict[str, float]] = None



@dataclass
class SessionState:
    session_id: str
    
    #study metadata
    study_phase: str
    engine_version: str
    config_snapshot: Dict[str, Any]
    assignment_namespace: str

    system_label: str  # A/B/C/D: order-group label shown to the participant
    condition_sequence: List[Condition]  # actual system sequence
    active_condition_index: int

    # fixed topic order for all participants
    topic_sequence: List[TopicItem]

    # each profile stores the new SFUIM state:
    # z, theta, q, s, last_k, last_dir, streak, k
    profiles_by_condition: Dict[Condition, Dict[str, Any]]

    turns: List[TurnLog]

    # how many chat turns have been produced under each condition
    turn_count_by_condition: Dict[Condition, int]

    # why each condition ended: "max_turns", "user_end", or None
    ended_reason_by_condition: Dict[Condition, Optional[str]]

    # post-study questionnaire results
    post_study: Optional[Dict[str, Any]] = None


class InMemoryStore:
    def __init__(self) -> None:
        self.sessions: Dict[str, SessionState] = {}

    def create_session(self, state: SessionState) -> None:
        self.sessions[state.session_id] = state

    def get(self, session_id: str) -> Optional[SessionState]:
        return self.sessions.get(session_id)


session_store = InMemoryStore()