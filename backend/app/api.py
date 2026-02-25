from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
import random



from app.models.schemas import (
    StartStudyRequest, StartStudyResponse,
    ChatRequest, ChatResponse,
    FeedbackRequest, FeedbackResponse,
    NextResponse
)
from app.core.storage import SessionState, TurnLog, session_store
from app.core.sfuim_engine import SFUIMConfig, new_profile, render_prompt, update_profile, render_baseline_prompt
from app.core.llm_interface import DummyLLM
from app.core.persistence import save_session
from app.core.assignment import assign_system_label_balanced, get_label_counts
from app.core.topic_handler import detect_new_topic, update_task_state


router = APIRouter()
cfg = SFUIMConfig()
llm = DummyLLM()
MAX_TURNS_PER_CONDITION = 10

DEV_MODE = True #这个是为了让我自主控制模型类型设置了，到真实实验阶段这个要改成False


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
    label = assign_system_label_balanced(dev_mode=DEV_MODE)
    seq = make_condition_sequence()

    state = SessionState(
        session_id=sid,
        system_label=label,
        condition_sequence=seq,
        active_condition_index=0,
        profiles_by_condition={c: new_profile() for c in seq},
        turns=[],
        turn_count_by_condition={c: 0 for c in seq},
        ended_reason_by_condition={c: None for c in seq},
    )

    # ✅ 关键：统一用 session_store（不要用 store）
    session_store.create_session(state)
    save_session(state) 
    return StartStudyResponse(session_id=sid, system_label=label)


@router.post("/study/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, req: ChatRequest):
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    if _is_finished(state):
        return ChatResponse(
            answer="本次实验已完成，感谢参与！",
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
            answer="该阶段已达到最大对话轮数（10轮）。请点击“结束对话”进入下一系统。",
            turn_index=len(state.turns),
            active_condition=condition,
            turn_in_condition=turns_in_cond,
            need_switch=True,
            is_finished=False,
        )
    
   # 取 session topic_mode（默认 detect）
    topic_mode = getattr(state, "topic_mode", "detect")  # "off" | "detect" | "update"

    topic_dbg = None
    topic_ref = profile.get("topic_ref", "")

    # 正常生成 prompt & answer
    if condition == "baseline":
        print("USING BASELINE PROMPT")
        prompt = render_baseline_prompt(req.message)
    else:
        print("USING SFUIM PROMPT")
        prompt = render_prompt(req.message, profile)

    # 2) topic handler（不影响 prompt）
    if topic_mode != "off":
        if topic_mode == "detect":
            drift, det = detect_new_topic(
                user_msg=req.message,
                current_task=topic_ref,
                jaccard_threshold=0.25,
            )
            topic_dbg = {
                "mode": "detect",
                "ref": topic_ref,
                "drift": drift,
                "det": det,
            }
            # ✅ 更新 reference：滑动窗口
            profile["topic_ref"] = req.message

        elif topic_mode == "update":
            # 你想要的“可选更新 topic 状态”接口：
            # update_task_state 会维护 profile["task"] / task_history 等
            profile, upd_dbg = update_task_state(
                profile,
                req.message,
                jaccard_threshold=0.25,
                keep_history=True,
            )
            # 同时也做 drift 判定（以 topic_ref 或 profile["task"] 为基准都行）
            drift, det = detect_new_topic(
                user_msg=req.message,
                current_task=topic_ref,
                jaccard_threshold=0.25,
            )
            topic_dbg = {
                "mode": "update",
                "ref": topic_ref,
                "drift": drift,
                "det": det,
                "update": upd_dbg,
            }
            profile["topic_ref"] = req.message
            
    state.profiles_by_condition[condition] = profile
    answer = llm.generate(prompt)

    state.turns.append(TurnLog(
        t=datetime.utcnow().isoformat(),
        condition=condition,
        user=req.message,
        prompt_sent=prompt,
        answer=answer,
        # ✅ topic debug fields（baseline 会是 None）
        topic_mode=(topic_dbg["mode"] if topic_dbg else None),
        topic_ref=(topic_dbg["ref"] if topic_dbg else None),
        topic_drift=(topic_dbg["drift"] if topic_dbg else None),
        topic_sim=(topic_dbg["det"].get("sim") if topic_dbg else None),
        topic_threshold=(topic_dbg["det"].get("threshold") if topic_dbg else None),
        topic_reason=(topic_dbg["det"].get("reason") if topic_dbg else None),
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
    if not is_finished:
        active_condition = state.condition_sequence[state.active_condition_index]

    active_profile = None if active_condition is None else state.profiles_by_condition.get(active_condition)

    # ✅ 你的 SessionState 里没有 turn_index/style_vector/satisfaction/time/frequency 这些字段
    # ✅ 正确返回：turn_count + active_condition + profile（里面才有你存的四因子/风格向量）
    return {
        "session_id": state.session_id,
        "system_label": state.system_label,
        "is_finished": is_finished,
        "active_condition_index": state.active_condition_index,
        "active_condition": active_condition,
        "active_profile": active_profile,
        "turn_count_by_condition": state.turn_count_by_condition,
        "turn_count_total": len(state.turns),
        "last_turn": None if not state.turns else {
            "t": state.turns[-1].t,
            "condition": state.turns[-1].condition,
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
        return NextResponse(is_finished=True, active_condition=None, active_condition_index=state.active_condition_index)

    current = _active_condition(state)

    # 如果没被 max_turns 结束，那就是用户主动结束
    if state.ended_reason_by_condition[current] is None:
        state.ended_reason_by_condition[current] = "user_end"

    ok = _advance_condition(state)
    
    if not ok:
        return NextResponse(is_finished=True, active_condition=None, active_condition_index=state.active_condition_index)

    new_cond = _active_condition(state)
    state.profiles_by_condition.setdefault(new_cond, new_profile())
    save_session(state)
    return NextResponse(is_finished=False, active_condition=new_cond, active_condition_index=state.active_condition_index)



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


