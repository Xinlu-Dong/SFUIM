from __future__ import annotations
from dataclasses import dataclass
from math import exp, log
from typing import Dict, Tuple




def clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class SFUIMConfig:
    r_max: int = 5
    eta: float = 0.18      # 学习率 η
    lambd: float = 0.22    # 时间衰减 λ
    gamma: float = 0.10    # 满意度头平滑 γ


def new_profile() -> Dict:
    # θ_C, θ_E, θ_S ∈ [-1,1], s ∈ [0,1]
    #C: Complexity; E: Examples; S: Structure
    #s: 初始满意度头
    return {
        "theta": {"C": 0.0, "E": 0.0, "S": 0.0},
        "s": 0.5,
        "last_k": {"C": 0, "E": 0, "S": 0},   # κ_j^{last}
        "count": {"C": 0, "E": 0, "S": 0},    # c_j^(k)
        "k": 0,  # 当前轮次计数（每次feedback后+1）
        "task": "",
        "task_history": [],
        "topic_ref": ""#上一轮用户消息（或上一轮“认为是同主题”的消息）

    }


def map_slot_to_text(theta: Dict[str, float]) -> Tuple[str, str, str]:
    # 你文档里的离散化映射（可后续精调）:contentReference[oaicite:8]{index=8}
    c = theta["C"]
    e = theta["E"]
    s = theta["S"]

    if c < -0.4:
        complexity_text = "请用非常通俗的方式解释，尽量避免专业术语。"
    elif c > 0.4:
        complexity_text = "可以进行较深入的技术分析，包括原理与实现细节。"
    else:
        complexity_text = "难度适中，先给整体直观解释，再补充必要细节。"

    if e < 0:
        examples_text = "不需要例子"
    elif e < 0.2:
        examples_text = "可以只用 0–1 个简单例子。"
    elif e > 0.6:
        examples_text = "请至少给出 2 个贴近实际场景的例子。"
    else:
        examples_text = "请给出 1–2 个代表性的例子。"

    if s < -0.5:
        structure_text = "可以采用自然段落的形式回答。风格偏向叙述性"
    elif s > 0.5:
        structure_text = "请使用清晰的小标题和分点结构组织回答。"
    else:
        structure_text = "建议使用分点结构回答。"

    return complexity_text, examples_text, structure_text


def render_prompt(task: str, profile: Dict) -> str:
    # 你文档里的模板 :contentReference[oaicite:9]{index=9}
    complexity_text, examples_text, structure_text = map_slot_to_text(profile["theta"])
    return (
        "[ROLE] 你是一名面向初学者的专业助教。\n\n"
        f"[TONE] {complexity_text}\n"
        f"       {examples_text}\n"
        f"       {structure_text}\n\n"
        f"[TASK] {task}\n\n"
        "[OUTPUT] 请用中文回答；保证内容准确，条理清晰。\n"
    )

def render_baseline_prompt(user_message: str) -> str:
    # baseline：固定模板，不读取 profile
    return user_message


def update_profile(
    cfg: SFUIMConfig,
    profile: Dict,
    rating: int,
    dC: int,
    dE: int,
    dS: int,
    condition: str,
) -> Dict:
    """
    condition:
      - full: 四因子全开
      - baseline: 不更新（固定prompt）
      - no_time: T=1
      - no_frequency: F=1
    """
    if condition == "baseline":
        return profile

    k = profile["k"] + 1
    profile["k"] = k

    # Level: L_k = r_k / R_max ; 我们用 |L_k| 控制步长 :contentReference[oaicite:10]{index=10}
    L = rating / cfg.r_max
    absL = abs(L)

    d = {"C": dC, "E": dE, "S": dS}

    for j in ["C", "E", "S"]:
        if d[j] == 0:
            continue

        # Time: T_{k,j} = exp(-λ Δk) :contentReference[oaicite:11]{index=11}
        if condition == "no_time":
            T = 1.0
        else:
            delta_k = k - profile["last_k"][j]
            T = exp(-cfg.lambd * delta_k)

        # Frequency: F_{k,j} = 1 + log(1 + c_j) :contentReference[oaicite:12]{index=12}
        if condition == "no_frequency":
            F = 1.0
        else:
            c = profile["count"][j]
            F = 1.0 + log(1.0 + c)

        delta_theta = cfg.eta * d[j] * absL * T * F
        profile["theta"][j] = clip(profile["theta"][j] + delta_theta, -1.0, 1.0)

        # 更新 last 与 count
        profile["last_k"][j] = k
        profile["count"][j] += 1

    # 满意度头 s_k：指数平滑（用于分析，不影响prompt）:contentReference[oaicite:13]{index=13}
    score_norm = (rating + cfg.r_max) / (2 * cfg.r_max)  # [-5,5] -> [0,1]
    profile["s"] = (1 - cfg.gamma) * profile["s"] + cfg.gamma * score_norm

    return profile
