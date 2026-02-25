import copy
import math

import pytest

from app.core.sfuim_engine import SFUIMConfig, new_profile, update_profile, clip


# ---------- helpers ----------
def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def expected_T(cfg: SFUIMConfig, k: int, last_k: int, condition: str) -> float:
    if condition == "no_time":
        return 1.0
    delta_k = k - last_k
    return math.exp(-cfg.lambd * delta_k)


def expected_F(cfg: SFUIMConfig, count_before: int, condition: str) -> float:
    if condition == "no_frequency":
        return 1.0
    # ⚠️ 你的实现：c = profile["count"][j]（更新前的次数）:contentReference[oaicite:1]{index=1}
    return 1.0 + math.log(1.0 + count_before)


def expected_delta_theta(cfg: SFUIMConfig, rating: int, d: int, T: float, F: float) -> float:
    L = rating / cfg.r_max
    absL = abs(L)
    return cfg.eta * d * absL * T * F


def expected_s_next(cfg: SFUIMConfig, s_prev: float, rating: int) -> float:
    score_norm = (rating + cfg.r_max) / (2 * cfg.r_max)  # [-r_max, r_max] -> [0,1]
    return (1 - cfg.gamma) * s_prev + cfg.gamma * score_norm


# ---------- tests ----------

def test_clip_bounds():
    assert clip(2.0) == 1.0
    assert clip(-2.0) == -1.0
    assert clip(0.3) == 0.3


@pytest.mark.parametrize("dC,sign", [(1, 1), (-1, -1)])
def test_theta_direction_matches_d_sign_when_rating_positive(dC, sign):
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.2, gamma=0.1)
    p = new_profile()
    p2 = update_profile(cfg, p, rating=5, dC=dC, dE=0, dS=0, condition="full")
    assert sign * p2["theta"]["C"] > 0


def test_baseline_no_update_anything():
    cfg = SFUIMConfig()
    p = new_profile()
    before = copy.deepcopy(p)
    p2 = update_profile(cfg, p, rating=5, dC=1, dE=1, dS=1, condition="baseline")

    # baseline: 你代码直接 return profile，不应改任何字段 :contentReference[oaicite:2]{index=2}
    assert p2 == before


@pytest.mark.parametrize("condition", ["full", "no_time", "no_frequency"])
def test_k_increments_when_not_baseline(condition):
    cfg = SFUIMConfig()
    p = new_profile()
    assert p["k"] == 0
    p2 = update_profile(cfg, p, rating=0, dC=0, dE=0, dS=0, condition=condition)
    assert p2["k"] == 1


def test_only_nonzero_d_slots_update_theta_lastk_count():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.2, gamma=0.1)
    p = new_profile()

    p2 = update_profile(cfg, p, rating=5, dC=1, dE=0, dS=-1, condition="full")

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


def test_time_formula_T_matches_exp_decay_in_full():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.5, gamma=0.1)
    p = new_profile()

    # Force next k = 10 and last_k=0 => delta_k=10
    p["k"] = 9
    p["last_k"]["C"] = 0
    p_before = copy.deepcopy(p)

    p2 = update_profile(cfg, p, rating=5, dC=1, dE=0, dS=0, condition="full")

    k = p_before["k"] + 1
    T = expected_T(cfg, k, p_before["last_k"]["C"], "full")
    F = expected_F(cfg, p_before["count"]["C"], "full")
    delta = expected_delta_theta(cfg, rating=5, d=1, T=T, F=F)

    assert approx(p2["theta"]["C"], clip(0.0 + delta), tol=1e-9)


def test_no_time_forces_T_equal_1_effect_on_update():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=1.0, gamma=0.1)

    p_full = new_profile()
    p_nt = new_profile()

    # make delta_k large
    p_full["k"] = 9
    p_full["last_k"]["C"] = 0
    p_nt["k"] = 9
    p_nt["last_k"]["C"] = 0

    full2 = update_profile(cfg, p_full, rating=5, dC=1, dE=0, dS=0, condition="full")
    nt2 = update_profile(cfg, p_nt, rating=5, dC=1, dE=0, dS=0, condition="no_time")

    # no_time should update more than full when lambda>0 and delta_k>0
    assert nt2["theta"]["C"] > full2["theta"]["C"]


def test_frequency_formula_F_matches_1_plus_log_1_plus_count_in_full():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.1)
    p = new_profile()

    # First update: count_before = 0 => F = 1 + log(1) = 1
    p1_before = copy.deepcopy(p)
    p1 = update_profile(cfg, p, rating=5, dC=1, dE=0, dS=0, condition="full")
    k1 = p1_before["k"] + 1
    T1 = expected_T(cfg, k1, p1_before["last_k"]["C"], "full")  # lambda=0 => 1
    F1 = expected_F(cfg, p1_before["count"]["C"], "full")       # count_before=0 => 1
    delta1 = expected_delta_theta(cfg, 5, 1, T1, F1)
    assert approx(p1["theta"]["C"], clip(0.0 + delta1), tol=1e-9)

    # Second update: count_before should now be 1 => F > 1
    p2_before = copy.deepcopy(p1)
    p2 = update_profile(cfg, p1, rating=5, dC=1, dE=0, dS=0, condition="full")
    k2 = p2_before["k"] + 1
    T2 = expected_T(cfg, k2, p2_before["last_k"]["C"], "full")  # still 1
    F2 = expected_F(cfg, p2_before["count"]["C"], "full")       # count_before=1 => 1 + log(2)
    delta2 = expected_delta_theta(cfg, 5, 1, T2, F2)
    assert approx(p2["theta"]["C"], clip(p2_before["theta"]["C"] + delta2), tol=1e-9)

    assert F2 > F1


def test_no_frequency_forces_F_equal_1_effect_on_update():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.1)
    p_full = new_profile()
    p_nf = new_profile()

    # Let full gain extra from frequency on second update; no_frequency will not
    full1 = update_profile(cfg, p_full, rating=5, dC=1, dE=0, dS=0, condition="full")
    nf1 = update_profile(cfg, p_nf, rating=5, dC=1, dE=0, dS=0, condition="no_frequency")

    full2 = update_profile(cfg, full1, rating=5, dC=1, dE=0, dS=0, condition="full")
    nf2 = update_profile(cfg, nf1, rating=5, dC=1, dE=0, dS=0, condition="no_frequency")

    # full should be >= no_frequency, and strictly greater by 2nd update (since F_full > 1)
    assert full2["theta"]["C"] >= nf2["theta"]["C"]
    assert full2["theta"]["C"] > nf2["theta"]["C"]


def test_level_absL_uses_absolute_rating():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.1)

    p_pos = new_profile()
    p_neg = new_profile()

    pos = update_profile(cfg, p_pos, rating=5, dC=1, dE=0, dS=0, condition="no_time")
    neg = update_profile(cfg, p_neg, rating=-5, dC=1, dE=0, dS=0, condition="no_time")

    # absL uses absolute rating so magnitude should match (sign comes only from d)
    assert approx(pos["theta"]["C"], neg["theta"]["C"], tol=1e-9)


def test_satisfaction_head_exponential_smoothing_matches_formula():
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.0, gamma=0.2)
    p = new_profile()
    s0 = p["s"]

    # make sure we actually run update (not baseline) but with d=0 so theta doesn't matter
    p1 = update_profile(cfg, p, rating=5, dC=0, dE=0, dS=0, condition="full")
    expected1 = expected_s_next(cfg, s0, rating=5)
    assert approx(p1["s"], expected1, tol=1e-9)

    p2 = update_profile(cfg, p1, rating=-5, dC=0, dE=0, dS=0, condition="full")
    expected2 = expected_s_next(cfg, expected1, rating=-5)
    assert approx(p2["s"], expected2, tol=1e-9)


def test_clip_applied_when_step_is_huge():
    cfg = SFUIMConfig(r_max=5, eta=100.0, lambd=0.0, gamma=0.1)
    p = new_profile()
    p2 = update_profile(cfg, p, rating=5, dC=1, dE=0, dS=0, condition="no_time")
    assert p2["theta"]["C"] == 1.0


def test_time_and_frequency_both_affect_update_in_full():
    """
    Full should be <= no_time when lambda>0 and delta_k>0,
    and >= no_frequency when count_before>0 (2nd update).
    """
    cfg = SFUIMConfig(r_max=5, eta=0.2, lambd=0.8, gamma=0.1)

    # --- time effect ---
    p_full = new_profile()
    p_nt = new_profile()
    # delta_k large
    p_full["k"] = 9
    p_full["last_k"]["C"] = 0
    p_nt["k"] = 9
    p_nt["last_k"]["C"] = 0

    full_time = update_profile(cfg, p_full, rating=5, dC=1, dE=0, dS=0, condition="full")
    nt_time = update_profile(cfg, p_nt, rating=5, dC=1, dE=0, dS=0, condition="no_time")
    assert full_time["theta"]["C"] < nt_time["theta"]["C"]

    # --- frequency effect (2nd update) ---
    p_full2 = new_profile()
    p_nf2 = new_profile()
    full_a = update_profile(cfg, p_full2, rating=5, dC=1, dE=0, dS=0, condition="full")
    nf_a = update_profile(cfg, p_nf2, rating=5, dC=1, dE=0, dS=0, condition="no_frequency")
    full_b = update_profile(cfg, full_a, rating=5, dC=1, dE=0, dS=0, condition="full")
    nf_b = update_profile(cfg, nf_a, rating=5, dC=1, dE=0, dS=0, condition="no_frequency")
    assert full_b["theta"]["C"] > nf_b["theta"]["C"]