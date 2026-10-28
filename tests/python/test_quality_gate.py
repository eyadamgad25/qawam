"""Tests for qawam_ml/quality.py and ml/eval/gate_eval.py."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from qawam_ml.packs import MEDIAPIPE_INDEX as I
from qawam_ml.packs import load_packs, resolve_pack
from qawam_ml.quality import FEATURES, LogisticGate, rep_features, segment

EVAL_PATH = Path(__file__).resolve().parents[2] / "ml" / "eval" / "gate_eval.py"
spec = importlib.util.spec_from_file_location("gate_eval", EVAL_PATH)
gate_eval = importlib.util.module_from_spec(spec)
sys.modules["gate_eval"] = gate_eval
spec.loader.exec_module(gate_eval)

SQUAT = resolve_pack(load_packs()["lower-limb.squat"], "left")


def _squat(n=40, shoulder_half_width=5.0, noise=0.0, knee_depth=0.0, seed=0):
    """N x 33 x 5 landmarks of a squat seen from the side (narrow shoulders)."""
    rng = np.random.default_rng(seed)
    marks = np.zeros((n, 33, 5))
    marks[:, :, 3] = 0.9
    for f in range(n):
        bend = np.sin(np.pi * f / (n - 1))
        for side, dx in (("LEFT", -shoulder_half_width), ("RIGHT", shoulder_half_width)):
            marks[f, I[f"{side}_SHOULDER"], :2] = (200 + dx, 100 + 40 * bend)
            marks[f, I[f"{side}_HIP"], :2] = (200 + dx / 2, 250 + 60 * bend)
            marks[f, I[f"{side}_KNEE"], :2] = (200 + dx / 2 + 60 * bend, 380 - 20 * bend)
            marks[f, I[f"{side}_ANKLE"], :2] = (200 + dx / 2, 500)
            marks[f, I[f"{side}_KNEE"], 2] = knee_depth
    marks[:, :, :2] += rng.normal(0, noise, size=(n, 33, 2))
    return marks


def test_features_have_expected_keys_and_rom():
    feats = rep_features(_squat(), SQUAT)
    assert set(feats) == set(FEATURES)
    assert feats["detect_rate"] == 1.0
    assert feats["rom_deg"] > 30
    assert feats["vis_mean"] == pytest.approx(0.9)


def test_frontalness_separates_profile_from_frontal():
    profile = rep_features(_squat(shoulder_half_width=3), SQUAT)["frontalness"]
    frontal = rep_features(_squat(shoulder_half_width=60), SQUAT)["frontalness"]
    assert frontal > 3 * profile


def test_jitter_and_bone_variation_grow_with_noise():
    clean = rep_features(_squat(), SQUAT)
    noisy = rep_features(_squat(noise=8.0), SQUAT)
    assert noisy["jitter_deg"] > clean["jitter_deg"] + 1
    assert noisy["bone_cv"] > clean["bone_cv"]


def test_out_of_plane_flags_segment_pointing_at_camera():
    flat = rep_features(_squat(), SQUAT)["out_of_plane"]
    deep = rep_features(_squat(knee_depth=150.0), SQUAT)["out_of_plane"]
    assert deep > flat + 0.5


def test_undetected_frames_and_segment():
    marks = _squat()
    marks[::2] = np.nan
    feats = rep_features(marks, SQUAT)
    assert feats["detect_rate"] == pytest.approx(0.5)
    assert all(np.isfinite(v) for v in feats.values())
    frames = np.arange(100, 140)
    assert segment(frames, marks, 110, 119).shape[0] == 10
    assert rep_features(np.full((5, 33, 5), np.nan), SQUAT)["vis_mean"] == 0.0


def test_logistic_gate_learns_and_exports():
    rng = np.random.default_rng(1)
    rows = [{f: float(rng.normal()) for f in FEATURES} for _ in range(300)]
    y = [int(r["jitter_deg"] < 0) for r in rows]
    model = LogisticGate(FEATURES).fit(rows, y)
    assert gate_eval.auroc(model.predict(rows), y) > 0.95
    exported = model.to_json()
    assert exported["features"] == list(FEATURES) and len(exported["coef"]) == len(FEATURES)
    assert exported["coef"][FEATURES.index("jitter_deg")] < 0


def _units(n_people=5, per=60, seed=2):
    rng = np.random.default_rng(seed)
    units = []
    for p in range(n_people):
        for _ in range(per):
            wrong = int(rng.random() < 0.3)
            row = {f: float(rng.normal()) for f in FEATURES}
            row["out_of_plane"] += 2.5 * wrong
            row["vis_mean"] = float(rng.random())
            units.append({**row, "person_id": p, "wrong": wrong, "pack_id": "lower-limb.squat"})
    return units


def test_nested_gate_beats_visibility_when_geometry_is_informative():
    units = _units()
    combined = gate_eval.nested_gate(units, "combined", 0.1, 0.1, 1.0)
    visibility = gate_eval.nested_gate(units, "visibility", 0.1, 0.1, 1.0)
    assert visibility["coverage"] == 0.0
    assert combined["coverage"] > 0.3
    assert combined["false_cue_rate"] <= 0.15
    scores = gate_eval.out_of_fold(units, "combined", 1.0)
    boot = gate_eval.person_bootstrap(units, scores, gate_eval.out_of_fold(units, "visibility", 1.0), rounds=200)
    assert boot["ci95"][0] > 0


def test_aurc_is_lower_for_a_better_score():
    wrong = [0] * 50 + [1] * 50
    good = list(range(100, 0, -1))
    bad = list(range(100))
    assert gate_eval.aurc(good, wrong) < gate_eval.aurc(bad, wrong)


def test_view_rule_uses_view_labels_and_pack_view():
    units = []
    for p in range(3):
        for view, frontal in (("profile", 0.05), ("half-profile", 0.45), ("front", 0.7)):
            for pack in ("lower-limb.squat", "lower-limb.leg-abduction"):
                wrong = int((pack.endswith("squat") and view != "profile") or (pack.endswith("abduction") and view != "front"))
                units.append({"person_id": p, "view": view, "frontalness": frontal, "pack_id": pack, "wrong": wrong})
    rule = gate_eval.view_rule_gate(units)
    assert rule["overall"]["false_cue_rate"] == 0.0
    assert rule["overall"]["coverage"] == pytest.approx(1 / 3, abs=0.01)
    assert rule["cuts"][0] == (0.25, 0.575)
