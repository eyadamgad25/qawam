"""Tests for ml/eval/confirm_reference.py: leg choice, the two controls, and frozen cut-offs."""

import importlib.util
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("confirm_reference", EVAL_DIR / "confirm_reference.py")
c = importlib.util.module_from_spec(spec)
sys.modules["confirm_reference"] = c
spec.loader.exec_module(c)
q = c.q


def rep(i, y=0, offset=0.0, size=1.0, person="A"):
    wave = np.sin(np.linspace(0, np.pi, q.LENGTH))[:, None] * size
    ch = np.repeat(wave, 4, axis=1) + offset + np.random.default_rng(i).normal(0, 0.02, (q.LENGTH, 4))
    return q.Rep(dataset="t", person=person, exercise="e", group=(person,), order=(i,), incorrect=y, view="v", channels=ch,
                 seconds=2.0, jerk=0.1)


def test_moving_leg_is_the_ankle_that_travels():
    pts = np.zeros((10, 13, 2))
    pts[:, q.P["RIGHT_ANKLE"], 0] = np.linspace(0, 1, 10)
    assert c.moving_leg(pts) == "right"


def test_controls_tell_a_different_recording_from_a_different_movement():
    def auc(rows):
        return c.auc_ci(rows, "dtw")["auc"]

    new_day = [rep(i) for i in range(8)] + [rep(20 + i, 1, offset=1.0) for i in range(8)]  # same movement, shifted posture
    assert auc(c.plain_gap(c.start_posture(new_day))) > 0.95  # control 1 raises the alarm
    assert auc(q.personalise(c.remove_start(new_day), 3)) < 0.8  # control 2 removes the fake signal
    fault = [rep(i) for i in range(8)] + [rep(20 + i, 1, size=0.5) for i in range(8)]
    assert auc(q.personalise(c.remove_start(fault), 3)) > 0.95  # a real fault survives it


def test_decisions_use_only_the_given_cut_offs():
    rows = q.personalise([rep(i, int(i > 4)) for i in range(9)], 3)
    c.apply_cuts(rows, {"dtw": -1.0, "dtw_z": 1e9})
    assert all(r["dtw_says"] for r in rows) and not any(r["dtw_z_says"] for r in rows)


def test_keraal_joint_names_match_the_files():
    assert c.KERAAL_NAMES["LEFT_SHOULDER"] == "Left_shoulder" and c.KERAAL_NAMES["RIGHT_ANKLE"] == "Right_ankle"
