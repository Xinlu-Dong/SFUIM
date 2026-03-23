from pydantic import BaseModel, Field
from typing import Literal, Optional


SystemLabel = Literal["A", "B", "C", "D"]  # shown to users only
Condition = Literal["full", "baseline", "no_time", "no_frequency"]


class StartStudyRequest(BaseModel):
    participant_id: Optional[str] = None


class StartStudyResponse(BaseModel):
    session_id: str
    system_label: SystemLabel
    active_condition_index: int
    current_topic_id: str
    current_topic_title: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    turn_index: int

    # for frontend workflow control
    active_condition: Optional[Condition] = None
    turn_in_condition: int = 0
    need_switch: bool = False
    is_finished: bool = False


class NextResponse(BaseModel):
    ok: bool = True
    is_finished: bool
    active_condition: Optional[Condition] = None
    active_condition_index: int
    current_topic_id: Optional[str] = None
    current_topic_title: Optional[str] = None


class FeedbackRequest(BaseModel):
    # overall rating r_k: [-5, 5]
    rating: int = Field(ge=-5, le=5)

    # continuous feedback d_{k,j} in [-1, 1]
    d_complexity: float = Field(ge=-1.0, le=1.0)
    d_examples: float = Field(ge=-1.0, le=1.0)
    d_structure: float = Field(ge=-1.0, le=1.0)


class FeedbackResponse(BaseModel):
    ok: bool = True


class PostStudyRequest(BaseModel):
    age_range: str
    gender: str
    education_level: str
    field_of_study: str

    easiest_system: str
    best_learning_match: str

    adaptation_rating: int = Field(ge=1, le=5)
    confidence_rating: int = Field(ge=1, le=5)
    use_again: str

    helpful_aspects: Optional[str] = ""
    improvement_suggestions: Optional[str] = ""


class PostStudyResponse(BaseModel):
    ok: bool = True