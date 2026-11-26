"""Tests for ml/eval/two_day_eval.py on stick figures: file checks, rep splitting, day 1 references, the pass rule."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("two_day_eval", EVAL_DIR / "two_day_eval.py")
t = importlib.util.module_from_spec(spec)
sys.modules["two_day_eval"] = t
spec.loader.exec_module(t)
q = t.q
CUTS = {"dtw": 0.2, "dtw_z": 1.05}


def figure(angle_deg, exercise):
    """13 points: a person whose main joint is angle_deg away from rest."""
    a = np.radians(angle_deg)
    pts = {"HEAD": (0, -0.6)}
    for side, s in (("LEFT", -1), ("RIGHT", 1)):
        pts |= {f"{side}_SHOULDER": (0.2 * s, 0), f"{side}_ELBOW": (0.2 * s, 0.5), f"{side}_WRIST": (0.2 * s, 1.0),
                f"{side}_HIP": (0.15 * s, 1.0), f"{side}_KNEE": (0.15 * s, 1.7), f"{side}_ANKLE": (0.15 * s, 2.4)}
    if exercise == "armabd":
        pts["RIGHT_ELBOW"] = (0.2 + 0.5 * np.sin(a), 0.5 * np.cos(a))
        pts["RIGHT_WRIST"] = (0.2 + np.sin(a), np.cos(a))
    elif exercise == "legabd":
        pts["RIGHT_KNEE"] = (0.15 + 0.7 * np.sin(a), 1 + 0.7 * np.cos(a))
        pts["RIGHT_ANKLE"] = (0.15 + 1.4 * np.sin(a), 1 + 1.4 * np.cos(a))
    else:
        for side, s in (("LEFT", -1), ("RIGHT", 1)):
            pts[f"{side}_ANKLE"] = (0.15 * s + 0.7 * np.sin(a), 1.7 + 0.7 * np.cos(a))
    return [pts[n] for n in q.POINTS]


def video(exercise, peak, reps=8, seed=0, shift=0.0):
    rng = np.random.default_rng(seed)
    angles = [np.full(40, 2.0)]
    for _ in range(reps):
        angles += [2 + (peak * rng.normal(1, 0.03) - 2) * np.sin(np.linspace(0, np.pi, 45)) ** 2, np.full(25, 2.0)]
    pts = np.array([figure(x, exercise) for x in np.concatenate(angles)]) * 300 + (600 + shift, 200)
    return pts + rng.normal(0, 1.0, pts.shape)


@pytest.mark.parametrize("exercise,peak", [("squat", 90), ("legabd", 40), ("armabd", 90)])
def test_every_rep_is_found(exercise, peak):
    assert len(t.split_reps(video(exercise, peak), exercise)) == 8


def test_file_names_are_checked_before_anything_runs():
    full = [f"P01_D{d}_squat_{c}" for d in "12" for c in ("ok", "fault")]
    assert t.check_files(full) == []
    assert t.check_files(full[:-1]) == ["missing: P01_D2_squat_fault"]
    assert "name not understood" in t.check_files([*full, "Ahmed_day1"])[0]


def everyone(day2_factor=1.0):
    reps = []
    for p in range(8):
        own = 60 + 6 * p
        for d in (1, 2):
            for c, factor in (("ok", 1.0), ("fault", 0.5)):
                peak = own * factor * (day2_factor if d == 2 and c == "ok" else 1)
                reps += t.reps_of(f"P{p + 1:02d}_D{d}_squat_{c}", video("squat", peak, seed=100 * p + 10 * d + (c == "fault"), shift=40 * d), 30.0)
    return reps


def test_references_come_from_day_1_and_are_never_scored():
    rows = q.personalise(everyone(), 3)
    first = [r for r in rows if r["rep"].view == "day 1" and not r["y"]]
    assert min(r["rep"].order[2] for r in first) == 3


def test_rule_passes_a_method_that_works_and_fails_when_day_2_looks_different():
    good = t.build_report(everyone(), [], 32, {"dtw": 0.5, "dtw_z": 4.0})
    assert good["verdict"]["checks"]["at least 8 people"]
    assert good["day 2"]["per_patient"]["macro_f1"] > 0.9
    bad = t.build_report(everyone(day2_factor=0.6), [], 32, {"dtw": 0.5, "dtw_z": 4.0})
    assert not bad["verdict"]["passed"]


def test_too_many_unusable_videos_fail_the_test():
    report = t.build_report(everyone(), ["x"] * 9, 32, CUTS)
    assert not report["verdict"]["checks"]["at most a quarter of the videos left out"]
