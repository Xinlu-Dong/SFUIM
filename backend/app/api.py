from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
import random
import os

from app.models.schemas import (
    StartStudyRequest, StartStudyResponse,
    ChatRequest, ChatResponse,
    FeedbackRequest, FeedbackResponse,
    NextResponse
)
from app.core.storage import SessionState, TurnLog, session_store
from app.core.sfuim_engine import SFUIMConfig, new_profile, render_prompt, update_profile, render_baseline_prompt
from app.core.llm_interface import get_llm
from app.core.persistence import save_session
from app.core.assignment import assign_system_label_balanced, get_label_counts, get_condition_sequence_for_label
from app.core.topic_assignment import assign_topic_label_balanced, build_topic_sequence

router = APIRouter()
cfg = SFUIMConfig()
#llm = DummyLLM()
llm = get_llm()
print("LLM_BACKEND =", os.getenv("LLM_BACKEND"))
print("OLLAMA_BASE_URL =", os.getenv("OLLAMA_BASE_URL"))
MAX_TURNS_PER_CONDITION = 10

DEV_MODE = False #这个是为了让我自主控制模型类型设置了，到真实实验阶段这个要改成False

@router.post("/dev/force_condition")
def force_condition(session_id: str, condition: str):
    if not DEV_MODE:
        raise HTTPException(status_code=403, detail="Dev mode disabled")

    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    if condition not in state.condition_sequence:
        raise HTTPException(
            status_code=400,
            detail=f"Condition must be one of {state.condition_sequence}",
        )

    # 强制切换 active_condition_index
    state.active_condition_index = state.condition_sequence.index(condition)
    state.profiles_by_condition.setdefault(condition, new_profile())
    save_session(state)

    return {"ok": True, "forced_to": condition}


@router.get("/dev/label_counts")
def dev_label_counts():
    return get_label_counts(dev_mode=DEV_MODE)



@router.post("/study/start", response_model=StartStudyResponse)
def start_study(req: StartStudyRequest):
    sid = uuid4().hex

    # system order (existing)
    label = assign_system_label_balanced(dev_mode=DEV_MODE)
    seq = get_condition_sequence_for_label(label)

    # NEW: topic order (independent from system order)
    topic_order_label = assign_topic_label_balanced(dev_mode=DEV_MODE)
    topic_sequence = build_topic_sequence(topic_order_label)

    state = SessionState(
        session_id=sid,
        system_label=label,
        condition_sequence=seq,
        active_condition_index=0,

        topic_order_label=topic_order_label,
        topic_sequence=topic_sequence,

        profiles_by_condition={c: new_profile() for c in seq},
        turns=[],
        turn_count_by_condition={c: 0 for c in seq},
        ended_reason_by_condition={c: None for c in seq},
    )

    session_store.create_session(state)
    save_session(state)

    current_topic = topic_sequence[0]
    return StartStudyResponse(
        session_id=sid,
        system_label=label,
        active_condition_index=0,
        current_topic_id=current_topic["id"],
        current_topic_title=current_topic["title"],
    )


@router.post("/study/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, req: ChatRequest):
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    if _is_finished(state):
        return ChatResponse(
            answer="This study session is complete. Thank you for your participation!",
            turn_index=len(state.turns),
            active_condition=None,
            turn_in_condition=0,
            need_switch=False,
            is_finished=True,
        )

    condition = _active_condition(state)
    profile = state.profiles_by_condition[condition]
    turns_in_cond = state.turn_count_by_condition[condition]

    # ✅ 满 10 轮：不再继续回答，提示必须切换
    if turns_in_cond >= MAX_TURNS_PER_CONDITION:
        state.ended_reason_by_condition[condition] = "max_turns"
        save_session(state)
        return ChatResponse(
            answer="This system has reached the maximum number of dialogue turns (10). Please click 'End and continue' to move to the next system.",
            turn_index=len(state.turns),
            active_condition=condition,
            turn_in_condition=turns_in_cond,
            need_switch=True,
            is_finished=False,
        )
    
    # 正常生成 prompt & answer
    if condition == "baseline":
        print("USING BASELINE PROMPT")
        prompt = render_baseline_prompt(req.message)
    else:
        print("USING SFUIM PROMPT")
        prompt = render_prompt(req.message, profile)

    
    state.profiles_by_condition[condition] = profile
    answer = llm.generate(prompt)

    current_topic = state.topic_sequence[state.active_condition_index]
    state.turns.append(TurnLog(
        t=datetime.utcnow().isoformat(),
        condition=condition,
        topic_id=current_topic["id"],
        topic_title=current_topic["title"],
        user=req.message,
        prompt_sent=prompt,
        answer=answer,
    ))

    # ✅ 当前条件轮数 +1
    state.turn_count_by_condition[condition] += 1
    turns_in_cond = state.turn_count_by_condition[condition]

    save_session(state)

    return ChatResponse(
        answer=answer,
        turn_index=len(state.turns),
        active_condition=condition,
        turn_in_condition=turns_in_cond,
        need_switch=False,
        is_finished=False,
    )


@router.post("/study/{session_id}/feedback", response_model=FeedbackResponse)
def feedback(session_id: str, req: FeedbackRequest):
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    if not state.turns:
        raise HTTPException(status_code=400, detail="No turns to attach feedback to")

    if state.active_condition_index >= len(state.condition_sequence):
        raise HTTPException(status_code=400, detail="Study already finished")
    condition = state.condition_sequence[state.active_condition_index]
    profile = state.profiles_by_condition[condition]

    # 把反馈写回最后一轮
    last = state.turns[-1]
    last.rating = req.rating
    last.d_complexity = req.d_complexity
    last.d_examples = req.d_examples
    last.d_structure = req.d_structure

    # 更新画像（baseline 不更新；no_time/no_frequency 做消融）    
    # ✅ baseline：只记录反馈，不更新画像
    if condition != "baseline":
        profile = update_profile(
            cfg=cfg,
            profile=profile,
            rating=req.rating,
            dC=req.d_complexity,
            dE=req.d_examples,
            dS=req.d_structure,
            condition=condition,
        )
    state.profiles_by_condition[condition] = profile
    save_session(state)

    return FeedbackResponse(ok=True)


@router.get("/study/{session_id}/state")
def get_state(session_id: str):
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    is_finished = state.active_condition_index >= len(state.condition_sequence)

    active_condition = None
    current_topic = None

    if not is_finished:
        active_condition = state.condition_sequence[state.active_condition_index]
        current_topic = state.topic_sequence[state.active_condition_index]

    active_profile = None if active_condition is None else state.profiles_by_condition.get(active_condition)

    return {
        "session_id": state.session_id,
        "system_label": state.system_label,
        "is_finished": is_finished,
        "active_condition_index": state.active_condition_index,
        "active_condition": active_condition,

        # NEW
        "topic_order_label": state.topic_order_label,
        "current_topic_id": None if current_topic is None else current_topic["id"],
        "current_topic_title": None if current_topic is None else current_topic["title"],

        "active_profile": active_profile,
        "turn_count_by_condition": state.turn_count_by_condition,
        "turn_count_total": len(state.turns),
        "last_turn": None if not state.turns else {
            "t": state.turns[-1].t,
            "condition": state.turns[-1].condition,
            "topic_id": state.turns[-1].topic_id,
            "topic_title": state.turns[-1].topic_title,
            "user": state.turns[-1].user,
            "rating": state.turns[-1].rating,
            "d_complexity": state.turns[-1].d_complexity,
            "d_examples": state.turns[-1].d_examples,
            "d_structure": state.turns[-1].d_structure,
        }
    }

@router.post("/study/{session_id}/next", response_model=NextResponse)
def next_condition(session_id: str):
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    if _is_finished(state):
        return NextResponse(
            is_finished=True,
            active_condition=None,
            active_condition_index=state.active_condition_index,
            current_topic_id=None,
            current_topic_title=None,
        )

    current = _active_condition(state)

    # 如果没被 max_turns 结束，那就是用户主动结束
    if state.ended_reason_by_condition[current] is None:
        state.ended_reason_by_condition[current] = "user_end"

    ok = _advance_condition(state)
    if not ok:
        save_session(state)
        return NextResponse(
            is_finished=True,
            active_condition=None,
            active_condition_index=state.active_condition_index,
            current_topic_id=None,
            current_topic_title=None,
        )

    new_cond = _active_condition(state)
    state.profiles_by_condition.setdefault(new_cond, new_profile())

    new_topic = state.topic_sequence[state.active_condition_index]

    save_session(state)
    return NextResponse(
        is_finished=False,
        active_condition=new_cond,
        active_condition_index=state.active_condition_index,
        current_topic_id=new_topic["id"],
        current_topic_title=new_topic["title"],
    )


def _is_finished(state: SessionState) -> bool:
    return state.active_condition_index >= len(state.condition_sequence)

def _active_condition(state: SessionState) -> str:
    return state.condition_sequence[state.active_condition_index]

def _advance_condition(state: SessionState) -> bool:
    """切换到下一个条件。成功返回 True；没有下一个则进入 finished 并返回 False。"""
    if state.active_condition_index < len(state.condition_sequence) - 1:
        state.active_condition_index += 1
        return True
    state.active_condition_index = len(state.condition_sequence)
    return False


