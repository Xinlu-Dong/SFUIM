from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


SystemLabel = Literal["A", "B", "C"]
Condition = Literal["full", "baseline", "no_time", "no_frequency"]


class StartStudyRequest(BaseModel):
    participant_id: Optional[str] = None  # 允许空，后端生成也行


class StartStudyResponse(BaseModel):
    session_id: str
    system_label: SystemLabel


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    turn_index: int
    # 前端控制用:
    active_condition: Optional[str] = None#哪种模型
    turn_in_condition: int = 0
    need_switch: bool = False#是否切换模型
    is_finished: bool = False#是否结束当前模型对话

class NextResponse(BaseModel):
    ok: bool = True
    is_finished: bool
    active_condition: Optional[str] = None
    active_condition_index: int


class FeedbackRequest(BaseModel):
    # 整体评分 r_k：[-5, 5]
    rating: int = Field(ge=-5, le=5)

    # 三维 d_{k,j} in {-1,0,1}
    d_complexity: int = Field(ge=-1, le=1)
    d_examples: int = Field(ge=-1, le=1)
    d_structure: int = Field(ge=-1, le=1)


class FeedbackResponse(BaseModel):
    ok: bool = True
