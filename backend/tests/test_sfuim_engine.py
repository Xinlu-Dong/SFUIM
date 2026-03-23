import math
import pytest

from app.core.sfuim_engine import (
    DIMS,
    SFUIMConfig,
    clip,
    sign0,
    new_profile,
    normalize_profile,
    quantize_value,
    map_policy_to_prompt,
    render_prompt,
    render_baseline_prompt,
    update_profile,
)


def test_clip_basic():
    assert clip(0.5) == 0.5
    assert clip(2.0) == 1.0
    assert clip(-3.0) == -1.0
    assert clip(5.0, 0.0, 10.0) == 5.0
    assert clip(-1.0, 0.0, 10.0) == 0.0
    assert clip(11.0, 0.0, 10.0) == 10.0


def test_sign0_basic():
    assert sign0(0.5) == 1
    assert sign0(-0.5) == -1
    assert sign0(0.0) == 0
    assert sign0(1e-8) == 0
    assert sign0(-1e-8) == 0
    assert sign0(1e-4, eps=1e-6) == 1
    assert sign0(-1e-4, eps=1e-6) == -1


def test_new_profile_has_new_model_structure():
    p = new_profile()

    assert set(p.keys()) == {
        "z", "theta", "q", "s", "last_k", "last_dir", "streak", "k"
    }

    for axis in DIMS:
        assert p["z"][axis] == 0.0
        assert p["theta"][axis] == 0.0
        assert p["q"][axis] == 0
        assert p["last_k"][axis] == 0
        assert p["last_dir"][axis] == 0
        assert p["streak"][axis] == 0

    assert p["s"] == 0.5
    assert p["k"] == 0


def test_normalize_profile_none_returns_new_profile():
    p = normalize_profile(None)
    fresh = new_profile()
    assert p == fresh


def test_normalize_profile_accepts_new_format():
    raw = {
        "z": {"C": 1.2, "E": -0.7, "S": 0.3},
        "theta": {"C": 0.5, "E": -0.4, "S": 0.1},
        "q": {"C": 1, "E": -1, "S": 0},
        "s": 0.7,
        "last_k": {"C": 2, "E": 3, "S": 4},
        "last_dir": {"C": 1, "E": -1, "S": 0},
        "streak": {"C": 2, "E": 1, "S": 0},
        "k": 4,
    }

    p = normalize_profile(raw)

    assert p["z"]["C"] == 1.2
    assert p["z"]["E"] == -0.7
    assert p["theta"]["C"] == 0.5
    assert p["q"]["E"] == -1
    assert p["s"] == 0.7
    assert p["last_k"]["S"] == 4
    assert p["last_dir"]["E"] == -1
    assert p["streak"]["C"] == 2
    assert p["k"] == 4


def test_normalize_profile_migrates_old_format():
    cfg = SFUIMConfig()
    old = {
        "theta": {"C": 0.4, "E": -0.2, "S": 0.0},
        "s": 0.6,
        "last_k": {"C": 2, "E": 0, "S": 1},
        "count": {"C": 5, "E": 1, "S": 0},  # old field should be ignored
        "k": 3,
    }

    p = normalize_profile(old, cfg)

    assert set(p.keys()) == {
        "z", "theta", "q", "s", "last_k", "last_dir", "streak", "k"
    }
    assert p["theta"]["C"] == 0.4
    assert p["theta"]["E"] == -0.2
    assert p["theta"]["S"] == 0.0
    assert p["s"] == 0.6
    assert p["last_k"]["C"] == 2
    assert p["k"] == 3

    # old profile has no direction/streak info, so they reset
    assert p["last_dir"] == {"C": 0, "E": 0, "S": 0}
    assert p["streak"] == {"C": 0, "E": 0, "S": 0}

    # z should be approximately recovered from theta
    assert math.isclose(math.tanh(cfg.beta * p["z"]["C"]), 0.4, rel_tol=1e-6, abs_tol=1e-6)
    assert math.isclose(math.tanh(cfg.beta * p["z"]["E"]), -0.2, rel_tol=1e-6, abs_tol=1e-6)
    assert math.isclose(math.tanh(cfg.beta * p["z"]["S"]), 0.0, rel_tol=1e-6, abs_tol=1e-6)


@pytest.mark.parametrize(
    "x, expected",
    [
        (-1.0, -2),
        (-0.7, -2),
        (-0.65 - 1e-9, -2),
        (-0.65, -1),
        (-0.3, -1),
        (-0.2 - 1e-9, -1),
        (-0.2, 0),
        (0.0, 0),
        (0.199999, 0),
        (0.2, 1),
        (0.5, 1),
        (0.649999, 1),
        (0.65, 2),
        (0.9, 2),
    ],
)
def test_quantize_value_default_thresholds(x, expected):
    cfg = SFUIMConfig()
    assert quantize_value(x, cfg) == expected


def test_map_policy_to_prompt_uses_q_not_theta():
    cfg = SFUIMConfig()
    profile = {
        "z": {"C": 0.0, "E": 0.0, "S": 0.0},
        "theta": {"C": 0.0, "E": 0.0, "S": 0.0},
        "q": {"C": 2, "E": 1, "S": 2},
        "s": 0.8,
        "last_k": {"C": 0, "E": 0, "S": 0},
        "last_dir": {"C": 0, "E": 0, "S": 0},
        "streak": {"C": 0, "E": 0, "S": 0},
        "k": 0,
    }

    role, complexity_rule, examples_rule, structure_rule, repair_rule = map_policy_to_prompt(profile, cfg)

    assert "domain expert" in role.lower()
    assert "technical language" in complexity_rule.lower() or "implementation" in complexity_rule.lower()
    assert "two practical examples" in examples_rule.lower() or "two contrasting examples" in examples_rule.lower()
    assert "fixed structure" in structure_rule.lower() or "headings" in structure_rule.lower()
    assert repair_rule == ""


def test_map_policy_to_prompt_triggers_repair_when_s_low():
    cfg = SFUIMConfig(repair_tau=0.4)
    profile = new_profile()
    profile["s"] = 0.2

    _, _, _, _, repair_rule = map_policy_to_prompt(profile, cfg)

    assert repair_rule != ""
    assert "did not match" in repair_rule.lower() or "style shift" in repair_rule.lower()


def test_render_prompt_contains_user_message_and_policy():
    cfg = SFUIMConfig()
    profile = new_profile()
    profile["q"] = {"C": 1, "E": 1, "S": 2}
    profile["s"] = 0.9

    prompt = render_prompt("Explain deadlock simply.", profile, cfg)

    assert "[ROLE]" in prompt
    assert "[STYLE POLICY]" in prompt
    assert "[USER MESSAGE]" in prompt
    assert "Explain deadlock simply." in prompt
    assert "qC=1" in prompt
    assert "qE=1" in prompt
    assert "qS=2" in prompt
    assert "[OUTPUT REQUIREMENTS]" in prompt


def test_render_baseline_prompt_uses_neutral_profile():
    cfg = SFUIMConfig()
    prompt = render_baseline_prompt("What is a mutex?", cfg)

    assert "[STYLE POLICY]" in prompt
    assert "qC=0" in prompt
    assert "qE=0" in prompt
    assert "qS=0" in prompt
    assert "What is a mutex?" in prompt


def test_update_profile_baseline_only_updates_s_and_k():
    cfg = SFUIMConfig(gamma=0.1)
    profile = new_profile()

    updated = update_profile(
        cfg=cfg,
        profile=profile,
        rating=5,
        dC=1.0,
        dE=1.0,
        dS=1.0,
        condition="baseline",
    )

    # k and s update
    assert updated["k"] == 1
    expected_s = (1 - 0.1) * 0.5 + 0.1 * 1.0
    assert math.isclose(updated["s"], expected_s, rel_tol=1e-9, abs_tol=1e-9)

    # no profile learning
    for axis in DIMS:
        assert updated["z"][axis] == 0.0
        assert updated["theta"][axis] == 0.0
        assert updated["q"][axis] == 0
        assert updated["last_k"][axis] == 0
        assert updated["last_dir"][axis] == 0
        assert updated["streak"][axis] == 0


def test_update_profile_full_positive_single_axis():
    cfg = SFUIMConfig(
        eta_min=0.05,
        eta_max=0.22,
        gamma=0.1,
        alpha=0.65,
        beta=2.0,
    )
    profile = new_profile()

    updated = update_profile(
        cfg=cfg,
        profile=profile,
        rating=5,
        dC=1.0,
        dE=0.0,
        dS=0.0,
        condition="full",
    )

    # s_next = 0.55, so eta_k should be based on s_next
    expected_s = 0.55
    expected_eta = cfg.eta_min + (cfg.eta_max - cfg.eta_min) * (1.0 - expected_s)
    expected_A = 1.0
    expected_F = 1.0 + cfg.alpha * math.log(1)  # first same-direction feedback
    expected_zC = 1.0 * 0.0 + expected_eta * 1.0 * expected_A * expected_F
    expected_thetaC = math.tanh(cfg.beta * expected_zC)
    expected_qC = quantize_value(expected_thetaC, cfg)

    assert updated["k"] == 1
    assert math.isclose(updated["s"], expected_s, rel_tol=1e-9, abs_tol=1e-9)

    assert math.isclose(updated["z"]["C"], expected_zC, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(updated["theta"]["C"], expected_thetaC, rel_tol=1e-9, abs_tol=1e-9)
    assert updated["q"]["C"] == expected_qC

    assert updated["last_k"]["C"] == 1
    assert updated["last_dir"]["C"] == 1
    assert updated["streak"]["C"] == 1

    # untouched axes
    for axis in ("E", "S"):
        assert updated["z"][axis] == 0.0
        assert updated["theta"][axis] == 0.0
        assert updated["q"][axis] == 0
        assert updated["last_k"][axis] == 0
        assert updated["last_dir"][axis] == 0
        assert updated["streak"][axis] == 0


def test_update_profile_negative_feedback_sets_negative_direction():
    cfg = SFUIMConfig()
    profile = new_profile()

    updated = update_profile(
        cfg=cfg,
        profile=profile,
        rating=-5,
        dC=-1.0,
        dE=0.0,
        dS=0.0,
        condition="full",
    )

    assert updated["z"]["C"] < 0
    assert updated["theta"]["C"] < 0
    assert updated["q"]["C"] <= 0
    assert updated["last_dir"]["C"] == -1
    assert updated["streak"]["C"] == 1
    assert updated["last_k"]["C"] == 1


def test_zero_direction_does_not_update_last_dir_last_k_or_streak():
    cfg = SFUIMConfig()
    profile = new_profile()

    updated = update_profile(
        cfg=cfg,
        profile=profile,
        rating=5,
        dC=0.0,
        dE=0.0,
        dS=0.0,
        condition="full",
    )

    for axis in DIMS:
        assert updated["z"][axis] == 0.0
        assert updated["theta"][axis] == 0.0
        assert updated["q"][axis] == 0
        assert updated["last_k"][axis] == 0
        assert updated["last_dir"][axis] == 0
        assert updated["streak"][axis] == 0


def test_same_direction_feedback_increases_streak_and_frequency():
    cfg = SFUIMConfig(
        eta_min=0.05,
        eta_max=0.22,
        gamma=0.1,
        alpha=0.65,
        beta=2.0,
    )
    profile = new_profile()

    p1 = update_profile(cfg, profile, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    z1 = p1["z"]["C"]

    p2 = update_profile(cfg, p1, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    z2 = p2["z"]["C"]

    assert p2["streak"]["C"] == 2
    assert p2["last_dir"]["C"] == 1
    assert p2["last_k"]["C"] == 2
    assert z2 > z1

    # Second update should have F > 1 because streak == 2
    expected_F_second = 1.0 + cfg.alpha * math.log(2)
    assert expected_F_second > 1.0


def test_direction_change_resets_streak():
    cfg = SFUIMConfig()
    profile = new_profile()

    p1 = update_profile(cfg, profile, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    assert p1["streak"]["C"] == 1
    assert p1["last_dir"]["C"] == 1

    p2 = update_profile(cfg, p1, rating=5, dC=-1.0, dE=0.0, dS=0.0, condition="full")
    assert p2["streak"]["C"] == 1
    assert p2["last_dir"]["C"] == -1
    assert p2["last_k"]["C"] == 2


def test_no_frequency_disables_frequency_growth():
    cfg = SFUIMConfig(
        eta_min=0.05,
        eta_max=0.22,
        gamma=0.1,
        alpha=0.65,
        beta=2.0,
    )

    p_full = new_profile()
    p_full = update_profile(cfg, p_full, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    p_full = update_profile(cfg, p_full, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")

    p_nf = new_profile()
    p_nf = update_profile(cfg, p_nf, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_frequency")
    p_nf = update_profile(cfg, p_nf, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_frequency")

    assert p_full["streak"]["C"] == 2
    assert p_nf["streak"]["C"] == 2

    # Without frequency enhancement, growth should be smaller
    assert p_full["z"]["C"] > p_nf["z"]["C"]
    assert p_full["theta"]["C"] >= p_nf["theta"]["C"]


def test_time_decay_reduces_old_z_in_full_condition():
    cfg = SFUIMConfig(
        lambd=0.5,
        eta_min=0.1,
        eta_max=0.1,  # fixed eta for easier reasoning
        gamma=0.1,
        alpha=0.0,    # no frequency growth
        beta=1.0,
    )

    profile = new_profile()

    # First: update C positively
    p1 = update_profile(cfg, profile, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    z1 = p1["z"]["C"]

    # Second: only update E, so C receives no new directional push
    p2 = update_profile(cfg, p1, rating=5, dC=0.0, dE=1.0, dS=0.0, condition="full")
    z2 = p2["z"]["C"]

    # Because C had history and condition is full, old C state should decay
    assert z2 < z1
    assert p2["last_k"]["C"] == 1  # unchanged because no new non-zero C feedback
    assert p2["streak"]["C"] == 1  # unchanged


def test_no_time_keeps_old_z_without_decay():
    cfg = SFUIMConfig(
        lambd=0.5,
        eta_min=0.1,
        eta_max=0.1,
        gamma=0.1,
        alpha=0.0,
        beta=1.0,
    )

    profile = new_profile()

    p1 = update_profile(cfg, profile, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="no_time")
    z1 = p1["z"]["C"]

    p2 = update_profile(cfg, p1, rating=5, dC=0.0, dE=1.0, dS=0.0, condition="no_time")
    z2 = p2["z"]["C"]

    # no_time means rho = 1, and no new C increment is added, so C should stay the same
    assert math.isclose(z2, z1, rel_tol=1e-9, abs_tol=1e-9)


def test_theta_is_tanh_of_beta_times_z():
    cfg = SFUIMConfig(beta=2.5)
    profile = new_profile()

    updated = update_profile(
        cfg=cfg,
        profile=profile,
        rating=5,
        dC=0.6,
        dE=0.0,
        dS=0.0,
        condition="full",
    )

    assert math.isclose(
        updated["theta"]["C"],
        math.tanh(cfg.beta * updated["z"]["C"]),
        rel_tol=1e-9,
        abs_tol=1e-9,
    )


def test_q_is_quantization_of_theta():
    cfg = SFUIMConfig()
    profile = new_profile()

    updated = update_profile(
        cfg=cfg,
        profile=profile,
        rating=5,
        dC=1.0,
        dE=1.0,
        dS=-1.0,
        condition="full",
    )

    for axis in DIMS:
        assert updated["q"][axis] == quantize_value(updated["theta"][axis], cfg)


def test_low_satisfaction_produces_higher_learning_rate_than_high_satisfaction():
    cfg = SFUIMConfig(
        eta_min=0.05,
        eta_max=0.25,
        gamma=0.1,
        alpha=0.0,
        beta=1.0,
        lambd=0.0,
    )

    low_s_profile = new_profile()
    low_s_profile["s"] = 0.0

    high_s_profile = new_profile()
    high_s_profile["s"] = 1.0

    p_low = update_profile(cfg, low_s_profile, rating=1, dC=1.0, dE=0.0, dS=0.0, condition="full")
    p_high = update_profile(cfg, high_s_profile, rating=1, dC=1.0, dE=0.0, dS=0.0, condition="full")

    # Same rating and same directional input, but lower prior satisfaction should yield larger eta_k and thus larger z update
    assert p_low["z"]["C"] > p_high["z"]["C"]
    assert p_low["theta"]["C"] > p_high["theta"]["C"]


def test_rating_strength_A_affects_update_magnitude():
    cfg = SFUIMConfig(
        eta_min=0.1,
        eta_max=0.1,
        gamma=0.1,
        alpha=0.0,
        beta=1.0,
        lambd=0.0,
    )

    p_strong = update_profile(cfg, new_profile(), rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    p_weak = update_profile(cfg, new_profile(), rating=1, dC=1.0, dE=0.0, dS=0.0, condition="full")

    assert p_strong["z"]["C"] > p_weak["z"]["C"]
    assert p_strong["theta"]["C"] > p_weak["theta"]["C"]


def test_feedback_on_one_axis_can_decay_other_axis_in_full():
    cfg = SFUIMConfig(
        lambd=0.5,
        eta_min=0.1,
        eta_max=0.1,
        gamma=0.1,
        alpha=0.0,
        beta=1.0,
    )

    p0 = new_profile()
    p1 = update_profile(cfg, p0, rating=5, dC=1.0, dE=0.0, dS=0.0, condition="full")
    assert p1["z"]["C"] > 0

    p2 = update_profile(cfg, p1, rating=5, dC=0.0, dE=1.0, dS=0.0, condition="full")

    # C decays because full model always applies time decay to old state when that dimension has history
    assert p2["z"]["C"] < p1["z"]["C"]
    assert p2["z"]["E"] > 0
    assert p2["last_k"]["E"] == 2


def test_render_prompt_includes_repair_text_when_s_low():
    cfg = SFUIMConfig(repair_tau=0.4)
    profile = new_profile()
    profile["s"] = 0.1

    prompt = render_prompt("Explain semaphores.", profile, cfg)

    assert "did not match the user's preference well" in prompt or "style shift clearly noticeable" in prompt


def test_render_prompt_uses_new_user_message_label():
    cfg = SFUIMConfig()
    profile = new_profile()

    prompt = render_prompt("deeper", profile, cfg)

    assert "[USER MESSAGE]" in prompt
    assert "deeper" in prompt
    assert "[USER QUESTION]" not in prompt