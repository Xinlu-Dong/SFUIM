from __future__ import annotations

from dataclasses import dataclass
from math import atanh, exp, log, tanh
from typing import Dict, Optional, Tuple, List


DIMS: Tuple[str, str, str] = ("C", "E", "S")

# 将数值限制在给定区间内。
# 这里主要用于限制评分归一化结果、满意度和旧版 theta 的边界范围。
def clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# 将连续值转换为方向符号 {-1, 0, 1}。
# 用于判断当前反馈是正向、负向还是近似为 0，从而更新 last_dir 和 streak。
def sign0(x: float, eps: float = 1e-6) -> int:
    if x > eps:
        return 1
    if x < -eps:
        return -1
    return 0


@dataclass
class SFUIMConfig:
    r_max: int = 5

    # Level 因子最小更新下限：
    # 即使用户很满意（r=+r_max），也保留极轻微更新，避免系统完全冻结。
    a_floor: float = 0.05

    # 自适应学习率：满意度越低，更新越积极; 原max是0.22，为了减小影响，先变为0.11
    eta_min: float = 0.05
    eta_max: float = 0.11

    # Time / satisfaction / frequency
    lambd: float = 0.22
    gamma: float = 0.10
    alpha: float = 0.65

    # z -> theta 的平滑压缩强度
    beta: float = 2.0

    # q = Q(theta) 的 5 档阈值
    q_lo2: float = -0.65
    q_lo1: float = -0.20
    q_hi1: float = 0.20
    q_hi2: float = 0.65

    # 当最近满意度较低时，提示模型要让风格变化更明显
    # 我要删掉这个参数了，为了让SFUIM作用更纯粹
    #repair_tau: float = 0.40
    
    eps: float = 1e-6


# -----------------------------
# Profile helpers
# -----------------------------

# 将任意字典规范化为按 C/E/S 三轴组织的 float 字典。
# 如果某个维度缺失，则补上默认值。
def _axis_float(value: Dict | None, default: float = 0.0) -> Dict[str, float]:
    value = value or {}
    return {d: float(value.get(d, default)) for d in DIMS}


# 将任意字典规范化为按 C/E/S 三轴组织的 int 字典。
# 如果某个维度缺失，则补上默认值。
def _axis_int(value: Dict | None, default: int = 0) -> Dict[str, int]:
    value = value or {}
    return {d: int(value.get(d, default)) for d in DIMS}


# 创建一个新版 SFUIM profile 的初始状态。
# 该状态同时包含隐状态 z、连续偏好 theta、离散策略 q，以及满意度和历史反馈记录。
def new_profile() -> Dict:
    """
    新版状态：
      z      : 连续隐状态（无限域）
      theta  : 有界连续偏好，theta = tanh(beta * z)
      q      : 离散策略档位 {-2,-1,0,1,2}
      s      : 平滑满意度 [0,1]
      last_k : 最近一次收到非零反馈的轮次
      last_dir: 最近一次非零反馈方向 {-1,0,1}
      streak : 同方向连续反馈次数
      k      : 已更新轮次
    """
    return {
        "z": {d: 0.0 for d in DIMS},
        "theta": {d: 0.0 for d in DIMS},
        "q": {d: 0 for d in DIMS},
        "s": 0.5,
        "last_k": {d: 0 for d in DIMS},
        "last_dir": {d: 0 for d in DIMS},
        "streak": {d: 0 for d in DIMS},
        "k": 0,
    }


# 将旧版连续偏好 theta 近似反推回新版隐状态 z。
# 这个函数主要用于兼容旧 session 数据迁移。
def _theta_to_latent(theta: float, beta: float, eps: float) -> float:
    # 兼容旧 session：若只有 theta，则近似恢复 z = atanh(theta)/beta
    theta = clip(theta, -1.0 + eps, 1.0 - eps)
    if abs(theta) < eps:
        return 0.0
    return atanh(theta) / max(beta, eps)


# 将连续偏好值 x 映射为 5 档离散策略值 {-2, -1, 0, 1, 2}。
# 该离散结果会直接用于 prompt policy 的风格控制。
def quantize_value(x: float, cfg: SFUIMConfig) -> int:
    if x < cfg.q_lo2:
        return -2
    if x < cfg.q_lo1:
        return -1
    if x < cfg.q_hi1:
        return 0
    if x < cfg.q_hi2:
        return 1
    return 2


# 将输入 profile 统一规范化为新版结构。
# 该函数同时兼容新版 profile 和旧版 profile，避免历史数据导致运行出错。
def normalize_profile(profile: Dict | None, cfg: SFUIMConfig | None = None) -> Dict:
    """
    将 profile 规范化为新版结构。
    兼容两类输入：
    1. 新版 profile（已有 z/theta/q/last_dir/streak）
    2. 旧版 profile（只有 theta/s/last_k/count/k）
    """
    cfg = cfg or SFUIMConfig()

    if not isinstance(profile, dict):
        return new_profile()

    theta = _axis_float(profile.get("theta"))

    if "z" in profile and isinstance(profile.get("z"), dict):
        z = _axis_float(profile.get("z"))
    else:
        z = {d: _theta_to_latent(theta[d], cfg.beta, cfg.eps) for d in DIMS}

    if "q" in profile and isinstance(profile.get("q"), dict):
        q = _axis_int(profile.get("q"))
    else:
        q = {d: quantize_value(theta[d], cfg) for d in DIMS}

    last_k = _axis_int(profile.get("last_k"))

    # 旧版没有方向与 streak，做近似迁移：保守起见全部重置为 0
    last_dir = _axis_int(profile.get("last_dir")) if "last_dir" in profile else {d: 0 for d in DIMS}
    streak = _axis_int(profile.get("streak")) if "streak" in profile else {d: 0 for d in DIMS}

    return {
        "z": z,
        "theta": theta,
        "q": q,
        "s": clip(float(profile.get("s", 0.5)), 0.0, 1.0),
        "last_k": last_k,
        "last_dir": last_dir,
        "streak": streak,
        "k": max(0, int(profile.get("k", 0))),
    }


# -----------------------------
# Prompt policy mapping
# -----------------------------

# 根据复杂度离散档位 qC，生成对应的系统角色描述和复杂度风格规则。
# 复杂度越高，角色越偏向专家；复杂度越低，角色越偏向教学助理。
def _complexity_policy(qc: int) -> Tuple[str, str]:
    if qc <= -2:
        role = "You are a patient teaching assistant helping a beginner learner."
        rule = (
            "Keep the explanation very simple. Avoid formulas. Avoid dense jargon. "
            "If a technical term is necessary, explain it immediately in plain language."
        )
    elif qc == -1:
        role = "You are a supportive teaching assistant."
        rule = (
            "Keep the explanation simple and accessible. Use only light terminology and do not go too deep."
        )
    elif qc == 0:
        role = "You are a teaching assistant with solid domain knowledge."
        rule = (
            "Start intuitively, then add moderate detail only where it helps understanding."
        )
    elif qc == 1:
        role = "You are both a teaching assistant and a domain specialist."
        rule = (
            "Give a technical but still teachable explanation. Include mechanisms, trade-offs, or implementation detail when useful."
        )
    else:
        role = "You are a precise domain expert."
        rule = (
            "Use technical language accurately. Discuss mechanisms and trade-offs directly. You may use formulas or implementation detail when it improves precision."
        )
    return role, rule


# 根据例子偏好档位 qE，生成回答中例子的数量与形式要求。
# qE 越高，系统越倾向提供更多、更丰富的示例。
def _examples_policy(qe: int) -> str:
    if qe <= -2:
        return "Do not add examples unless absolutely necessary."
    if qe == -1:
        return "Use at most one very short example."
    if qe == 0:
        return "Use exactly one representative example if it helps understanding."
    if qe == 1:
        return "Use two practical examples."
    return "Use two contrasting examples or three short concrete examples."


# 根据结构偏好 qS 和例子偏好 qE，生成回答结构要求。
# 当结构偏好更强时，会使用更固定、更明显的答案模板。
def _structure_policy(qs: int, qe: int) -> str:
    if qs <= -2:
        return "Write as one short flowing paragraph."
    if qs == -1:
        return "Write one short paragraph plus one final takeaway sentence."
    if qs == 0:
        return "Use two short sections with light structure."
    if qs == 1:
        return "Use clear headings and bullet points."

    if qe >= 1:
        return (
            "Use the fixed structure: 1) Core idea 2) How it works 3) Examples 4) Key takeaway."
        )
    return (
        "Use the fixed structure: 1) Core idea 2) How it works 3) Practical note 4) Key takeaway."
    )

'''
# 根据当前满意度 s 判断是否需要触发 repair 提示。
# 当最近满意度较低时，额外要求模型让这次风格调整更明显。
def _repair_policy(s: float, cfg: SFUIMConfig) -> str:
    if s < cfg.repair_tau:
        return (
            "The recent answers likely did not match the user's preference well. "
            "Make the style shift clearly noticeable in this response instead of staying close to a neutral middle-ground style."
        )
    return ""
'''    


# 将 profile 中的离散策略 q 映射为 prompt 所需的完整风格规则集合。
# 返回值包括角色、复杂度规则、例子规则、结构规则和 repair 规则。
def map_policy_to_prompt(profile: Dict, cfg: SFUIMConfig | None = None) -> Tuple[str, str, str, str]:
    cfg = cfg or SFUIMConfig()
    profile = normalize_profile(profile, cfg)

    qc = int(profile["q"]["C"])
    qe = int(profile["q"]["E"])
    qs = int(profile["q"]["S"])

    role, complexity_rule = _complexity_policy(qc)
    examples_rule = _examples_policy(qe)
    structure_rule = _structure_policy(qs, qe)
    #repair_rule = _repair_policy(float(profile["s"]), cfg)

    return role, complexity_rule, examples_rule, structure_rule, #repair_rule



#追问处理函数，用于检测用户消息是否为追问，并结合当前系统 topic 和近期用户消息生成重写后的消息，以帮助模型更好地理解用户意图。
FOLLOWUP_PRONOUNS = {"it", "them", "they", "this", "that", "these", "those"}
FOLLOWUP_PATTERNS = [
    "difference between them",
    "difference between it",
    "what is the difference",
    "what's the difference",
    "how does it work",
    "how does that work",
    "why is that",
    "tell me more",
    "explain more",
]

def recent_user_messages_for_condition(state, condition: str, limit: int = 2) -> list[str]:
        msgs = [
            t.user.strip()
            for t in state.turns
            if t.condition == condition and t.user and t.user.strip()
        ]
        return msgs[-limit:]

def detect_and_rewrite_followup(
    user_message: str,
    topic_title: Optional[str],
    recent_user_messages: Optional[List[str]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Returns:
        (is_followup, rewritten_message)
    """
    msg = user_message.strip()
    lower = msg.lower()

    tokens = lower.replace("?", "").replace(".", "").split()
    has_pronoun = any(tok in FOLLOWUP_PRONOUNS for tok in tokens)
    has_pattern = any(p in lower for p in FOLLOWUP_PATTERNS)
    short_message = len(tokens) <= 8

    is_followup = has_pattern or (short_message and has_pronoun)
    
    if not is_followup:
        return False, None

    # 特化：如果 topic 是“X 和 Y 的区别”类型
    if topic_title:
        topic_lower = topic_title.lower()

        if "machine learning" in topic_lower and "traditional programming" in topic_lower:
            if "difference" in lower or "them" in lower:
                return True, "What is the difference between machine learning and traditional programming?"
            if "it" in lower or "that" in lower:
                return True, "Please explain machine learning and traditional programming in the context of their differences."

        if "cloud computing" in topic_lower and "local computing" in topic_lower:
            if "difference" in lower or "them" in lower:
                return True, "What is the difference between cloud computing and local computing?"

    # 泛化 fallback：把 topic 补进来
    if topic_title:
        return True, f"In the context of '{topic_title}', {msg}"

    return True, None


# 将当前用户消息和 profile 渲染成最终发给 LLM 的完整 prompt。
# 该 prompt 会显式包含角色设定、风格策略和输出要求。
def render_prompt(
    user_message: str, #用户本轮提问
    profile: Dict,#用户画像
    cfg: SFUIMConfig | None = None,#全局配置，包含学习率、阈值等超参数
    #这些参数是为了处理用户可能的追问
    topic_title: Optional[str] = None,#当前系统topic
    recent_user_messages: Optional[List[str]] = None,#用户追问
    rewritten_message: Optional[str] = None,#结合追问+主题+短期历史提问生成的重写消息
) -> str:
    cfg = cfg or SFUIMConfig()
    profile = normalize_profile(profile, cfg)
    role, complexity_rule, examples_rule, structure_rule = map_policy_to_prompt(profile, cfg)

    #repair_block = f"- {repair_rule}\n" if repair_rule else ""

    topic_block = ""
    if topic_title:
        topic_block = f"[TOPIC]\n{topic_title}\n\n"

    recent_context_block = ""
    if recent_user_messages:
        context_lines = "\n".join(f"- {msg}" for msg in recent_user_messages if msg.strip())
        if context_lines:
            recent_context_block = f"[RECENT USER CONTEXT]\n{context_lines}\n\n"

    normalized_block = ""
    if rewritten_message and rewritten_message.strip() and rewritten_message.strip() != user_message.strip():
        normalized_block = (
            "[NORMALISED USER INTENT]\n"
            f"{rewritten_message}\n\n"
        )
    return (
        f"[ROLE]\n{role}\n\n"
        f"{topic_block}"
        f"{recent_context_block}"
        "[STYLE POLICY]\n"
        f"- Complexity preference: qC={profile['q']['C']}\n"
        f"- Examples preference: qE={profile['q']['E']}\n"
        f"- Structure preference: qS={profile['q']['S']}\n"
        f"- {complexity_rule}\n"
        f"- {examples_rule}\n"
        f"- {structure_rule}\n"
        #f"{repair_block}\n"
        "[FOLLOW-UP RULE]\n"
        "- The current message may be a follow-up that uses pronouns or omitted references.\n"
        "- First resolve references using the TOPIC and RECENT USER CONTEXT.\n"
        "- If words such as 'it', 'them', 'that', 'this', or 'the difference' appear, infer the most likely referent from the recent dialogue.\n"
        "- If the reference is still genuinely ambiguous, ask one short clarification question instead of guessing.\n\n"
        "[CURRENT USER MESSAGE]\n"
        f"{user_message}\n\n"
        f"{normalized_block}"
        "[OUTPUT REQUIREMENTS]\n"
        "- Answer in English.\n"
        "- Be accurate and helpful.\n"
        "- Prioritise the NORMALISED USER INTENT if provided.\n"
        "- Respond directly to the user's current message, whether it is a question, a follow-up, a correction, or a clarification request.\n"
    )

# 渲染 baseline 条件下的固定中性 prompt。
# baseline 不进行个性化学习，但仍使用统一模板，以保证实验比较公平。
def render_baseline_prompt(
    user_message: str,
    cfg: SFUIMConfig | None = None,
    topic_title: Optional[str] = None,
    recent_user_messages: Optional[List[str]] = None,
    rewritten_message: Optional[str] = None,
) -> str:
    """
    baseline 不做个性化更新，但依然使用固定的中性 prompt scaffold，
    这样比较才是“adaptive vs fixed neutral prompt”，而不是“有上下文 vs 无上下文”。
    """
    cfg = cfg or SFUIMConfig()
    neutral_profile = {
        "z": {d: 0.0 for d in DIMS},
        "theta": {d: 0.0 for d in DIMS},
        "q": {d: 0 for d in DIMS},
        "s": 0.5,
        "last_k": {d: 0 for d in DIMS},
        "last_dir": {d: 0 for d in DIMS},
        "streak": {d: 0 for d in DIMS},
        "k": 0,
    }
    return render_prompt(
        user_message=user_message,
        profile=neutral_profile,
        cfg=cfg,
        topic_title=topic_title,
        recent_user_messages=recent_user_messages,
        rewritten_message=rewritten_message,
    )

# -----------------------------
# State update
# -----------------------------

# 根据用户评分和三维反馈更新 profile。
# 这是新版 SFUIM 的核心更新函数：先更新满意度，再按四因子更新 z，并派生出 theta 和 q。
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
    New SFUIM update:
      z_{k+1,j} = rho_{k,j} z_{k,j} + eta_k * d_{k,j} * A_k * F_{k,j}
      theta_{k+1,j} = tanh(beta * z_{k+1,j})
      q_{k+1,j} = Q(theta_{k+1,j})

    Level factor:
      A_k uses dissatisfaction-based scaling with a non-zero floor:
      A_k = a_floor + (1 - a_floor) * (r_max - r_k) / (2 * r_max)

    condition:
      - full: 四因子全开
      - baseline: 固定中性 prompt，不做个性化学习
      - no_time: 关闭时间衰减，rho = 1
      - no_frequency: 关闭频率增强，F = 1
    
    """
    profile = normalize_profile(profile, cfg)

    # 无论是否更新个性化，都先更新满意度头，便于调试与日志分析
    score_norm = clip((float(rating) + cfg.r_max) / (2 * cfg.r_max), 0.0, 1.0)
    s_next = (1 - cfg.gamma) * float(profile["s"]) + cfg.gamma * score_norm

    k = int(profile["k"]) + 1

    if condition == "baseline":
        profile["s"] = s_next
        profile["k"] = k
        return profile

    # Level factor:
    # 评分越低（越不满意），更新越强；
    # 评分越高（越满意），更新越弱；
    # 但保留一个最小更新下限 a_floor，避免高分时完全不更新。
    rating_value = clip(float(rating), -cfg.r_max, cfg.r_max)
    dissatisfaction = (cfg.r_max - rating_value) / (2 * cfg.r_max)  # maps [-r_max, r_max] -> [1, 0]
    A = cfg.a_floor + (1.0 - cfg.a_floor) * dissatisfaction
    A = clip(A, cfg.a_floor, 1.0)
    
    d = {
        "C": clip(float(dC), -1.0, 1.0),
        "E": clip(float(dE), -1.0, 1.0),
        "S": clip(float(dS), -1.0, 1.0),
    }

    eta_k = cfg.eta_min + (cfg.eta_max - cfg.eta_min) * (1.0 - s_next)
    old_z = {axis: float(profile["z"][axis]) for axis in DIMS}

    for axis in DIMS:
        # Time factor
        if condition == "no_time" or int(profile["last_k"][axis]) == 0:
            rho = 1.0
        else:
            delta_k = max(0, k - int(profile["last_k"][axis]))
            rho = exp(-cfg.lambd * delta_k)

        direction = sign0(d[axis], cfg.eps)

        # Frequency factor: only reward repeated feedback in the SAME direction
        if direction == 0:
            streak = int(profile["streak"][axis])
            F = 1.0
        else:
            if direction == int(profile["last_dir"][axis]):
                streak = int(profile["streak"][axis]) + 1
            else:
                streak = 1

            if condition == "no_frequency":
                F = 1.0
            else:
                F = 1.0 + cfg.alpha * log(streak)

        z_new = rho * old_z[axis] + eta_k * d[axis] * A * F
        theta_new = tanh(cfg.beta * z_new)
        q_new = quantize_value(theta_new, cfg)

        profile["z"][axis] = float(z_new)
        profile["theta"][axis] = float(theta_new)
        profile["q"][axis] = int(q_new)

        if direction != 0:
            profile["last_k"][axis] = k
            profile["last_dir"][axis] = direction
            profile["streak"][axis] = streak

    profile["s"] = float(s_next)
    profile["k"] = k
    return profile