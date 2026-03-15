import copy
import math

import pytest

from app.core.sfuim_engine import SFUIMConfig, new_profile, update_profile, clip


# ---------- helpers ----------
def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def expected_rho(cfg: SFUIMConfig, k: int, last_k: int, count_before: int, condition: str) -> float:
    """
    新模型里的时间因子：rho 只作用在旧 theta 上。
    若该维之前从未收到过非零反馈（count_before == 0），则 rho = 1。
    """
    if condition == "no_time":
        return 1.0
    if count_before == 0:
        return 1.0
    delta_k = k - last_k
    return math.exp(-cfg.lambd * delta_k)


def expected_F(cfg: SFUIMConfig, count_before: int, condition: str) -> float:
    """
    新模型里的频率因子：
    F = 1 + alpha * log(1 + count_before)
    """
    if condition == "no_frequency":
        return 1.0
    return 1.0 + cfg.alpha * math.log(1.0 + count_before)


def expected_delta_theta(cfg: SFUIMConfig, rating: float, d: float, F: float) -> float:
    """
    新模型里当前轮增量不再乘时间因子。
    """
    A = abs(rating) / cfg.r_max
    return cfg.eta * d * A * F


def expected_theta_next(
    cfg: SFUIMConfig,
    theta_prev: float,
    rating: float,
    d: float,
    k: int,
    last_k: int,
    count_before: int,
    condition: str,
) -> float:
    rho = expected_rho(cfg, k, last_k, count_before, condition)
    F = expected_F(cfg, count_before, condition)
    delta = expected_delta_theta(cfg, rating, d, F)
    return clip(rho * theta_prev + delta)


def expected_s_next(cfg: SFUIMConfig, s_prev: float, rating: int) -> float:
    score_norm = (rating + cfg.r_max) / (2 * cfg.r_max)  # [-r_max, r_max] -> [0,1]
    return (1 - cfg.gamma) * s_prev + cfg.gamma * score_norm


# ---------- tests ----------

def test_clip_bounds():
    assert clip(2.0) == 1.0
    assert clip(-2.0) == -1.0
    assert clip(0.3) == 0.3


@pytest.mark.parametrize("dC,sign", [(1.0, 1), (-1.0, -1)])
def test_theta_direction_matches_d_sign_when_rating_positive(dC, sign):
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.2, gamma=0.1, alpha=1.0)
    p = new_profile()
    p2 = update_profile(cfg, p, rating=5, dC=dC, dE=0.0, dS=0.0, condition="full")
    assert sign * p2["theta"]["C"] > 0


def test_baseline_no_update_anything():
    cfg = SFUIMConfig()
    p = new_profile()
    before = copy.deepcopy(p)
    p2 = update_profile(cfg, p, rating=5, dC=1.0, dE=1.0, dS=1.0, condition="baseline")
    assert p2 == before


@pytest.mark.parametrize("condition", ["full", "no_time", "no_frequency"])
def test_k_increments_when_not_baseline(condition):
    cfg = SFUIMConfig()
    p = new_profile()
    assert p["k"] == 0
    p2 = update_profile(cfg, p, rating=0, dC=0.0, dE=0.0, dS=0.0, condition=condition)
    assert p2["k"] == 1


def test_only_nonzero_d_slots_update_theta_lastk_count():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.2, gamma=0.1, alpha=1.0)
    p = new_profile()

    p2 = update_profile(cfg, p, rating=5, dC=1.0, dE=0.0, dS=-1.0, condition="full")

    # C and S updated
    assert p2["count"]["C"] == 1
    assert p2["count"]["S"] == 1
    assert p2["last_k"]["C"] == 1
    assert p2["last_k"]["S"] == 1
    assert p2["theta"]["C"] != 0.0
    assert p2["theta"]["S"] != 0.0

    # E unchanged
    assert p2["count"]["E"] == 0
    assert p2["last_k"]["E"] == 0
    assert p2["theta"]["E"] == 0.0


def test_first_nonzero_feedback_has_no_time_decay_effect():
    """
    若某维此前从未被显式更新过（count_before == 0），
    则 full 条件下 rho=1，与 no_time 一样。
    """
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.8, gamma=0.1, alpha=1.0)

    p_full = new_profile()
    p_nt = new_profile()

    # 即使把 k 拉大，只要 count_before=0，rho 仍应为 1
    p_full["k"] = 9
    p_full["last_k"]["C"] = 0

    p_nt["k"] = 9
    p_nt["last_k"]["C"] = 0

    full2 = update_profile(cfg, p_full, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    nt2 = update_profile(cfg, p_nt, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_time")

    assert approx(full2["theta"]["C"], nt2["theta"]["C"], tol=1e-9)


def test_time_decay_applies_to_old_theta_in_full():
    """
    新模型：时间因子只衰减旧 theta，不削弱当前新反馈。
    """
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.5, gamma=0.1, alpha=1.0)
    p = new_profile()

    # 先做一次更新，得到非零 theta 和 count=1
    p1 = update_profile(cfg, p, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")

    # 制造较大 gap：让下一轮 k=10，上一轮 last_k=1
    p_before = copy.deepcopy(p1)
    p_before["k"] = 9

    # 关键：单独保存“真正更新前”的快照
    before_snapshot = copy.deepcopy(p_before)

    p2 = update_profile(cfg, p_before, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")

    k = before_snapshot["k"] + 1
    theta_expected = expected_theta_next(
        cfg=cfg,
        theta_prev=before_snapshot["theta"]["C"],
        rating=5,
        d=1.0,
        k=k,
        last_k=before_snapshot["last_k"]["C"],
        count_before=before_snapshot["count"]["C"],
        condition="full",
    )

    assert approx(p2["theta"]["C"], theta_expected, tol=1e-9)


def test_no_time_forces_rho_equal_1_on_old_theta():
    """
    no_time 条件下，旧 theta 不衰减；因此当 theta_prev > 0 且 gap>0 时，
    no_time 的结果应大于 full。
    """
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=1.0, gamma=0.1, alpha=1.0)

    # 构造已有历史偏好的 profile
    p_full = new_profile()
    p_nt = new_profile()

    p_full["theta"]["C"] = 0.6
    p_full["count"]["C"] = 1
    p_full["last_k"]["C"] = 1
    p_full["k"] = 9

    p_nt["theta"]["C"] = 0.6
    p_nt["count"]["C"] = 1
    p_nt["last_k"]["C"] = 1
    p_nt["k"] = 9

    full2 = update_profile(cfg, p_full, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    nt2 = update_profile(cfg, p_nt, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_time")

    assert nt2["theta"]["C"] > full2["theta"]["C"]


def test_frequency_formula_matches_1_plus_alpha_log_1_plus_count():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.1, alpha=1.3)
    p = new_profile()

    # 第一次更新：count_before = 0 => F = 1
    p1_before = copy.deepcopy(p)
    p1 = update_profile(cfg, p, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")

    k1 = p1_before["k"] + 1
    theta1_expected = expected_theta_next(
        cfg=cfg,
        theta_prev=p1_before["theta"]["C"],
        rating=5,
        d=1.0,
        k=k1,
        last_k=p1_before["last_k"]["C"],
        count_before=p1_before["count"]["C"],
        condition="full",
    )
    assert approx(p1["theta"]["C"], theta1_expected, tol=1e-9)

    # 第二次更新：count_before = 1 => F > 1
    p2_before = copy.deepcopy(p1)
    p2 = update_profile(cfg, p1, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")

    k2 = p2_before["k"] + 1
    theta2_expected = expected_theta_next(
        cfg=cfg,
        theta_prev=p2_before["theta"]["C"],
        rating=5,
        d=1.0,
        k=k2,
        last_k=p2_before["last_k"]["C"],
        count_before=p2_before["count"]["C"],
        condition="full",
    )
    assert approx(p2["theta"]["C"], theta2_expected, tol=1e-9)

    F1 = expected_F(cfg, 0, "full")
    F2 = expected_F(cfg, 1, "full")
    assert F2 > F1


def test_no_frequency_forces_F_equal_1_effect_on_update():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.1, alpha=1.0)
    p_full = new_profile()
    p_nf = new_profile()

    full1 = update_profile(cfg, p_full, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    nf1 = update_profile(cfg, p_nf, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_frequency")

    full2 = update_profile(cfg, full1, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    nf2 = update_profile(cfg, nf1, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_frequency")

    assert full2["theta"]["C"] > nf2["theta"]["C"]


def test_continuous_feedback_strength_changes_update_magnitude():
    """
    d 从离散改成连续后，|d| 越大，更新幅度应越大。
    """
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.1, alpha=1.0)

    p_small = new_profile()
    p_large = new_profile()

    small = update_profile(cfg, p_small, rating=5, dC=0.2, dE=0.0, dS=0.0, condition="no_time")
    large = update_profile(cfg, p_large, rating=5, dC=0.8, dE=0.0, dS=0.0, condition="no_time")

    assert large["theta"]["C"] > small["theta"]["C"] > 0


def test_level_absL_uses_absolute_rating():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.1, alpha=1.0)

    p_pos = new_profile()
    p_neg = new_profile()

    pos = update_profile(cfg, p_pos, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_time")
    neg = update_profile(cfg, p_neg, rating=-5, dC=1.0, dE=0.0, dS=0.0, condition="no_time")

    assert approx(pos["theta"]["C"], neg["theta"]["C"], tol=1e-9)


def test_satisfaction_head_exponential_smoothing_matches_formula():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.2, alpha=1.0)
    p = new_profile()
    s0 = p["s"]

    p1 = update_profile(cfg, p, rating=5, dC=0.0, dE=0.0, dS=0.0, condition="full")
    expected1 = expected_s_next(cfg, s0, rating=5)
    assert approx(p1["s"], expected1, tol=1e-9)

    p2 = update_profile(cfg, p1, rating=-5, dC=0.0, dE=0.0, dS=0.0, condition="full")
    expected2 = expected_s_next(cfg, expected1, rating=-5)
    assert approx(p2["s"], expected2, tol=1e-9)


def test_clip_applied_when_step_is_huge():
    cfg = SFUIMConfig(r_max=5, eta=100.0, lambd=0.0, gamma=0.1, alpha=1.0)
    p = new_profile()
    p2 = update_profile(cfg, p, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_time")
    assert p2["theta"]["C"] == 1.0


def test_full_condition_shows_both_time_and_frequency_effects():
    """
    同时验证：
    1) time: 有历史 theta 且 gap>0 时，full < no_time
    2) frequency: 第二次更新时，full > no_frequency
    """
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.8, gamma=0.1, alpha=1.0)

    # --- time effect on old theta ---
    p_full = new_profile()
    p_nt = new_profile()

    p_full["theta"]["C"] = 0.6
    p_full["count"]["C"] = 1
    p_full["last_k"]["C"] = 1
    p_full["k"] = 9

    p_nt["theta"]["C"] = 0.6
    p_nt["count"]["C"] = 1
    p_nt["last_k"]["C"] = 1
    p_nt["k"] = 9

    full_time = update_profile(cfg, p_full, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    nt_time = update_profile(cfg, p_nt, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_time")
    assert full_time["theta"]["C"] < nt_time["theta"]["C"]

    # --- frequency effect on second update ---
    p_full2 = new_profile()
    p_nf2 = new_profile()

    full_a = update_profile(cfg, p_full2, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    nf_a = update_profile(cfg, p_nf2, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_frequency")

    full_b = update_profile(cfg, full_a, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    nf_b = update_profile(cfg, nf_a, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_frequency")

    assert full_b["theta"]["C"] > nf_b["theta"]["C"]