from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime, timezone
import os

from app.models.schemas import (
    StartStudyRequest, StartStudyResponse,
    ChatRequest, ChatResponse,
    FeedbackRequest, FeedbackResponse,
    NextResponse, PostStudyRequest, PostStudyResponse,
)
from app.core.storage import SessionState, TurnLog, session_store
from app.core.sfuim_engine import (
    SFUIMConfig,
    detect_and_rewrite_followup,
    export_config_snapshot,
    new_profile,
    recent_user_messages_for_condition,
    render_prompt,
    update_profile,
    render_baseline_prompt,
)
from app.core.llm_interface import get_llm
from app.core.persistence import save_session
from app.core.assignment import (
    assign_system_label_round_robin,
    get_condition_sequence_for_label,
    get_fixed_topic_sequence,
    get_label_counts,
)

router = APIRouter()
cfg = SFUIMConfig()
llm = get_llm()

print("LLM_BACKEND =", os.getenv("LLM_BACKEND"))
print("OLLAMA_BASE_URL =", os.getenv("OLLAMA_BASE_URL"))

MAX_TURNS_PER_CONDITION = 10
DEV_MODE = False

# ===== study batch metadata =====
STUDY_PHASE = "final_tuned_experiment"
ASSIGNMENT_NAMESPACE = "final"
ENGINE_VERSION = "v_final_tuned_2026_04_08"


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

    state.active_condition_index = state.condition_sequence.index(condition)
    state.profiles_by_condition.setdefault(condition, new_profile())
    save_session(state)

    return {"ok": True, "forced_to": condition}


@router.get("/dev/label_counts")
def dev_label_counts():
    if not DEV_MODE:
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    return get_label_counts(dev_mode=DEV_MODE, namespace=ASSIGNMENT_NAMESPACE)


@router.post("/study/start", response_model=StartStudyResponse)
def start_study(req: StartStudyRequest):
    sid = uuid4().hex
    label = assign_system_label_round_robin(
        dev_mode=DEV_MODE,
        namespace=ASSIGNMENT_NAMESPACE,
    )
    seq = get_condition_sequence_for_label(label)
    topic_sequence = get_fixed_topic_sequence()

    state = SessionState(
        session_id=sid,
        study_phase=STUDY_PHASE,
        engine_version=ENGINE_VERSION,
        config_snapshot=export_config_snapshot(cfg),
        assignment_namespace=ASSIGNMENT_NAMESPACE,
        system_label=label,
        condition_sequence=seq,
        active_condition_index=0,
        topic_sequence=topic_sequence,
        profiles_by_condition={c: new_profile() for c in seq},
        turns=[],
        turn_count_by_condition={c: 0 for c in seq},
        ended_reason_by_condition={c: None for c in seq},
        post_study=None,
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
    last = _latest_turn_for_active_condition(state)

    if last is not None and last.rating is None:
        raise HTTPException(
            status_code=400,
            detail="Please submit feedback for the previous answer before sending a new message.",
        )

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

    current_topic = state.topic_sequence[state.active_condition_index]
    topic_title = current_topic["title"]

    recent_user_messages = recent_user_messages_for_condition(
        state=state,
        condition=condition,
        limit=2,
    )

    is_followup, rewritten_message = detect_and_rewrite_followup(
        user_message=req.message,
        topic_title=topic_title,
        recent_user_messages=recent_user_messages,
    )

    if condition == "baseline":
        prompt = render_baseline_prompt(
            user_message=req.message,
            cfg=cfg,
            topic_title=topic_title,
            recent_user_messages=recent_user_messages,
            rewritten_message=rewritten_message,
        )
    else:
        prompt = render_prompt(
            user_message=req.message,
            profile=profile,
            cfg=cfg,
            topic_title=topic_title,
            recent_user_messages=recent_user_messages,
            rewritten_message=rewritten_message,
        )

    answer = llm.generate(prompt)

    state.turns.append(
        TurnLog(
            t=datetime.now(timezone.utc).isoformat(),
            condition=condition,
            topic_id=current_topic["id"],
            topic_title=current_topic["title"],
            user=req.message,
            prompt_sent=prompt,
            answer=answer,
            is_followup_detected=is_followup,
            rewritten_user_message=rewritten_message,
            topic_title_used=topic_title,
            recent_user_context_used=recent_user_messages,
            profile_used_z={k: float(v) for k, v in profile.get("z", {}).items()},
            profile_used_q={k: int(v) for k, v in profile.get("q", {}).items()},
            profile_used_theta={k: float(v) for k, v in profile.get("theta", {}).items()},
            profile_used_s=float(profile.get("s", 0.5)),
        )
    )

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

    if _is_finished(state):
        raise HTTPException(status_code=400, detail="Study already finished")

    condition = _active_condition(state)
    profile = state.profiles_by_condition[condition]
    last = _latest_turn_for_active_condition(state)

    if last is None:
        raise HTTPException(
            status_code=400,
            detail="No current turn in the active system to attach feedback to.",
        )

    if last.rating is not None:
        raise HTTPException(
            status_code=400,
            detail="Feedback for the latest turn has already been submitted.",
        )

    last.rating = req.rating
    last.d_complexity = req.d_complexity
    last.d_examples = req.d_examples
    last.d_structure = req.d_structure

    profile = update_profile(
        cfg=cfg,
        profile=profile,
        rating=req.rating,
        dC=req.d_complexity,
        dE=req.d_examples,
        dS=req.d_structure,
        condition=condition,
    )

    last.profile_after_feedback_z = {k: float(v) for k, v in profile.get("z", {}).items()}
    last.profile_after_feedback_q = {k: int(v) for k, v in profile.get("q", {}).items()}
    last.profile_after_feedback_theta = {k: float(v) for k, v in profile.get("theta", {}).items()}
    last.profile_after_feedback_s = float(profile.get("s", 0.5))

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
        "study_phase": state.study_phase,
        "engine_version": state.engine_version,
        "assignment_namespace": state.assignment_namespace,
        "system_label": state.system_label,
        "is_finished": is_finished,
        "active_condition_index": state.active_condition_index,
        "active_condition": active_condition,
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
    last = _latest_turn_for_active_condition(state)

    if last is not None and last.rating is None:
        raise HTTPException(
            status_code=400,
            detail="Please submit feedback for the last answer before ending this system.",
        )

    if state.ended_reason_by_condition[current] is None:
        if state.turn_count_by_condition[current] >= MAX_TURNS_PER_CONDITION:
            state.ended_reason_by_condition[current] = "max_turns"
        else:
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


@router.post("/study/{session_id}/post-study", response_model=PostStudyResponse)
def submit_post_study(session_id: str, req: PostStudyRequest):
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    if not _is_finished(state):
        raise HTTPException(status_code=400, detail="Study not finished yet")

    state.post_study = {
        "age_range": req.age_range,
        "gender": req.gender,
        "education_level": req.education_level,
        "field_of_study": req.field_of_study,
        "easiest_system": req.easiest_system,
        "best_learning_match": req.best_learning_match,
        "adaptation_rating": req.adaptation_rating,
        "confidence_rating": req.confidence_rating,
        "use_again": req.use_again,
        "helpful_aspects": req.helpful_aspects,
        "improvement_suggestions": req.improvement_suggestions,
    }

    save_session(state)
    return PostStudyResponse(ok=True)


def _is_finished(state: SessionState) -> bool:
    return state.active_condition_index >= len(state.condition_sequence)


def _active_condition(state: SessionState) -> str:
    return state.condition_sequence[state.active_condition_index]


def _latest_turn_for_active_condition(state: SessionState):
    if _is_finished(state) or not state.turns:
        return None
    last = state.turns[-1]
    return last if last.condition == _active_condition(state) else None


def _advance_condition(state: SessionState) -> bool:
    if state.active_condition_index < len(state.condition_sequence) - 1:
        state.active_condition_index += 1
        return True
    state.active_condition_index = len(state.condition_sequence)
    return False