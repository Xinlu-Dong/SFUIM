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
    alpha: float = 1.0     # Frequency 因子系数 α


def new_profile() -> Dict:
    # θ_C, θ_E, θ_S ∈ [-1,1], s ∈ [0,1]
    # C: Complexity; E: Examples; S: Structure
    return {
        "theta": {"C": 0.0, "E": 0.0, "S": 0.0},
        "s": 0.5,
        "last_k": {"C": 0, "E": 0, "S": 0},   # κ_j^{last}
        "count": {"C": 0, "E": 0, "S": 0},    # c_{k,j}
        "k": 0,  # 当前轮次计数（每次 feedback 后 +1）
    }


def map_slot_to_text(theta: Dict[str, float]) -> Tuple[str, str, str]:
    c = theta["C"]
    e = theta["E"]
    s = theta["S"]

    if c < -0.4:
        complexity_text = "Explain in a very simple and beginner-friendly way. Avoid heavy jargon."
    elif c > 0.4:
        complexity_text = "Provide a deeper technical explanation, including principles and implementation details where useful."
    else:
        complexity_text = "Keep the explanation at a moderate level: start intuitive, then add necessary detail."

    if e < 0:
        examples_text = "Use few or no examples unless truly necessary."
    elif e < 0.2:
        examples_text = "Use at most one simple example if it helps."
    elif e > 0.6:
        examples_text = "Include at least two practical and concrete examples."
    else:
        examples_text = "Include one or two representative examples."

    if s < -0.5:
        structure_text = "A natural paragraph style is acceptable. The tone can be slightly narrative."
    elif s > 0.5:
        structure_text = "Use a clearly structured answer with headings and bullet points where appropriate."
    else:
        structure_text = "Prefer a clear, moderately structured answer."

    return complexity_text, examples_text, structure_text


def render_prompt(user_message: str, profile: Dict) -> str:
    complexity_text, examples_text, structure_text = map_slot_to_text(profile["theta"])

    return (
        "[ROLE] You are a professional teaching assistant helping a beginner learner.\n\n"
        f"[STYLE]\n"
        f"- {complexity_text}\n"
        f"- {examples_text}\n"
        f"- {structure_text}\n\n"
        f"[USER QUESTION]\n{user_message}\n\n"
        "[OUTPUT REQUIREMENTS]\n"
        "- Answer in English.\n"
        "- Be accurate, clear, and helpful.\n"
        "- Directly answer the user's question first.\n"
    )


def render_baseline_prompt(user_message: str) -> str:
    # baseline：固定模板，不读取 profile
    return user_message


def update_profile(
    cfg: SFUIMConfig,
    profile: Dict,
    rating: float,
    dC: float,
    dE: float,
    dS: float,
    condition: str,
) -> Dict:
    """
    condition:
      - full: 四因子全开
      - baseline: 用户原话直接作为 prompt，不进行任何风格调整
      - no_time: 关闭时间衰减，rho = 1
      - no_frequency: 关闭频率增强，F = 1
    """
    if condition == "baseline":
        return profile

    # 当前更新轮次
    k = profile["k"] + 1

    # Level factor: A_k = |r_k| / R_max
    A = abs(rating) / cfg.r_max

    # 连续反馈 d_{k,j} ∈ [-1, 1]
    d = {
        "C": clip(float(dC), -1.0, 1.0),
        "E": clip(float(dE), -1.0, 1.0),
        "S": clip(float(dS), -1.0, 1.0),
    }

    # 保留旧 theta，避免本轮更新互相污染
    old_theta = profile["theta"].copy()

    for j in ["C", "E", "S"]:
        # Step 3: Time factor rho_{k,j}
        if condition == "no_time":
            rho = 1.0
        else:
            if profile["count"][j] == 0:
                # 该维此前从未收到过非零反馈
                rho = 1.0
            else:
                delta_k = k - profile["last_k"][j]
                rho = exp(-cfg.lambd * delta_k)

        # Step 4: 对旧 profile 做时间衰减
        decayed_theta = rho * old_theta[j]

        # Step 5: Frequency factor
        if condition == "no_frequency":
            F = 1.0
        else:
            count = profile["count"][j]
            F = 1.0 + cfg.alpha * log(1.0 + count)

        # Step 6: 当前轮增量（不再乘 Time）
        delta_theta = cfg.eta * d[j] * A * F

        # Step 7: 更新 profile
        profile["theta"][j] = clip(decayed_theta + delta_theta, -1.0, 1.0)

        # Step 8: 只有该维收到非零反馈时，才更新 last_k 和 count
        if d[j] != 0:
            profile["last_k"][j] = k
            profile["count"][j] += 1

    # Step 9: 满意度头 s_k 指数平滑
    score_norm = (rating + cfg.r_max) / (2 * cfg.r_max)  # [-5,5] -> [0,1]
    profile["s"] = (1 - cfg.gamma) * profile["s"] + cfg.gamma * score_norm

    # 最后更新轮次
    profile["k"] = k

    return profile