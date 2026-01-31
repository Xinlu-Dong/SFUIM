from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
import random

from app.models.schemas import (
    StartStudyRequest, StartStudyResponse,
    ChatRequest, ChatResponse,
    FeedbackRequest, FeedbackResponse,
)
from app.core.storage import SessionState, TurnLog, session_store
from app.core.sfuim_engine import SFUIMConfig, new_profile, render_prompt, update_profile
from app.core.llm_interface import DummyLLM

router = APIRouter()
cfg = SFUIMConfig()
llm = DummyLLM()


def make_condition_sequence() -> list[str]:
    """
    每人用 3 种系统：full + baseline + (no_time or no_frequency)
    第三个条件随机；顺序随机，降低顺序效应。
    """
    third = random.choice(["no_time", "no_frequency"])
    seq = ["full", "baseline", third]
    random.shuffle(seq)
    return seq


def assign_system_label() -> str:
    # 注意：你现在是随机 A/B/C，但并不保证均衡
    return random.choice(["A", "B", "C"])


@router.post("/study/start", response_model=StartStudyResponse)
def start_study(req: StartStudyRequest):
    sid = uuid4().hex
    label = assign_system_label()
    seq = make_condition_sequence()

    state = SessionState(
        session_id=sid,
        system_label=label,
        condition_sequence=seq,
        active_condition_index=0,
        profile=new_profile(),
        turns=[],
        turn_count_by_condition={c: 0 for c in seq},
    )

    # ✅ 关键：统一用 session_store（不要用 store）
    session_store.create_session(state)

    return StartStudyResponse(session_id=sid, system_label=label)

MAX_TURNS_PER_CONDITION = 10

@router.post("/study/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, req: ChatRequest):
    # ✅ storage.py 里 get() 已经改成返回 Optional 了
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    # session 完成判断
    if state.active_condition_index >= len(state.condition_sequence):
        raise HTTPException(status_code=400, detail="Study already finished")

    condition = state.condition_sequence[state.active_condition_index]

    if state.turn_count_by_condition[condition] >= MAX_TURNS_PER_CONDITION:
        switched = _advance_condition(state)
        if not switched:
            # 已经没有下一条件了
            return ChatResponse(
                answer="本次实验已完成，感谢参与！",
                turn_index=len(state.turns),
                did_switch=True,
                is_finished=True,
                active_condition=None,
            )
        condition = state.condition_sequence[state.active_condition_index]

    # TODO: 未来加 Task&Topic handler
    prompt = render_prompt(req.message, state.profile)
    answer = llm.generate(prompt)
    '''
    turn = TurnLog(
        t=datetime.utcnow().isoformat(),
        user=req.message,
        prompt_sent=prompt,
        answer=answer,
    )
    '''

    #state.turns.append(turn)
    state.turns.append(TurnLog(
        t=datetime.utcnow().isoformat(),
        user=req.message,
        prompt_sent=prompt,
        answer=answer,
    ))
    state.turn_count_by_condition[condition] += 1

    return ChatResponse(
        answer=answer, 
        turn_index=len(state.turns),
        did_switch=False,
        is_finished=False,
        active_cpndition=condition,
        )

def _advance_condition(state: SessionState) -> bool:
    if state.active_condition_index < len(state.condition_sequence) - 1:
        state.active_condition_index += 1
        return True
    # 让 index 指向“完成态”
    state.active_condition_index = len(state.condition_sequence)
    return False


@router.post("/study/{session_id}/feedback", response_model=FeedbackResponse)
def feedback(session_id: str, req: FeedbackRequest):
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    if not state.turns:
        raise HTTPException(status_code=400, detail="No turns to attach feedback to")

    condition = state.condition_sequence[state.active_condition_index]

    # 把反馈写回最后一轮
    last = state.turns[-1]
    last.rating = req.rating
    last.d_complexity = req.d_complexity
    last.d_examples = req.d_examples
    last.d_structure = req.d_structure

    # 更新画像（baseline 不更新；no_time/no_frequency 做消融）
    state.profile = update_profile(
        cfg=cfg,
        profile=state.profile,
        rating=req.rating,
        dC=req.d_complexity,
        dE=req.d_examples,
        dS=req.d_structure,
        condition=condition,
    )

    # 简单策略：每次 feedback 就切换到下一个 condition（最多3个）
    #if state.active_condition_index < len(state.condition_sequence) - 1:
     #   state.active_condition_index += 1

    return FeedbackResponse(ok=True)


@router.get("/study/{session_id}/state")
def get_state(session_id: str):
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    is_finished = state.active_condition_index >= len(state.condition_sequence)
    active_condition = None
    if not is_finished:
        active_condition = state.condition_sequence[state.active_condition_index]

    # ✅ 你的 SessionState 里没有 turn_index/style_vector/satisfaction/time/frequency 这些字段
    # ✅ 正确返回：turn_count + active_condition + profile（里面才有你存的四因子/风格向量）
    return {
        "session_id": state.session_id,
        "system_label": state.system_label,
        "is_finished": is_finished,
        "active_condition_index": state.active_condition_index,
        "active_condition": active_condition,
        "turn_count_by_condition": state.turn_count_by_condition,
        "turn_count_total": len(state.turns),
        "profile": state.profile,
        "last_turn": None if not state.turns else {
            "t": state.turns[-1].t,
            "user": state.turns[-1].user,
            "rating": state.turns[-1].rating,
            "d_complexity": state.turns[-1].d_complexity,
            "d_examples": state.turns[-1].d_examples,
            "d_structure": state.turns[-1].d_structure,
        }
    }

@router.post("/study/{session_id}/next")
def next_condition(session_id: str):
    state = session_store.get(session_id)   # ✅ 改这里：store -> session_store
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    ok = _advance_condition(state)
    if not ok:
        return {"ok": True, "is_finished": True}

    current = state.condition_sequence[state.active_condition_index]
    return {
        "ok": True,
        "is_finished": False,
        "active_condition_index": state.active_condition_index,
        "active_condition": current,
    }

