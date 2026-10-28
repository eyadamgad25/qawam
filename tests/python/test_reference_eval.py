"""Tests for ml/eval/reference_eval.py on synthetic squat curves."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

EVAL_PATH = Path(__file__).resolve().parents[2] / "ml" / "eval" / "reference_eval.py"
spec = importlib.util.spec_from_file_location("reference_eval", EVAL_PATH)
reference_eval = importlib.util.module_from_spec(spec)
sys.modules["reference_eval"] = reference_eval
spec.loader.exec_module(reference_eval)

RepCurves = reference_eval.RepCurves


def _rep(person, number, correct, depth, video="PM_1", split="train"):
    rep = SimpleNamespace(
        person_id=person,
        repetition_number=number,
        correctness=int(correct),
        video_id=video,
        cam17_orientation="front",
    )
    curve = depth * np.sin(np.linspace(0, np.pi, 40))
    item = RepCurves(split, rep, 18, "profile", "lower-limb.squat", "knee_flexion")
    item.curves = {"left:knee_flexion": curve, "right:knee_flexion": curve.copy()}
    return item


def test_roc_auc():
    assert reference_eval.roc_auc([0.9, 0.8, 0.1], [1, 1, 0]) == 1.0
    assert reference_eval.roc_auc([0.5, 0.5], [1, 0]) == 0.5
    assert reference_eval.roc_auc([0.1], [1]) is None


def test_personal_reference_is_first_correct_rep():
    reps = [_rep(1, 1, False, 50), _rep(1, 2, True, 90), _rep(1, 3, True, 92)]
    refs = reference_eval.personal_references(reps)
    assert next(iter(refs.values())) is reps[1]


def test_personal_reference_beats_population_when_people_differ():
    # Each person squats to their own depth; an incorrect rep is 25 deg shallower than their own.
    train, evaluate = [], []
    for person, depth in ((1, 60), (2, 110)):
        for n in range(1, 7):
            train.append(_rep(person, n, n != 6, depth - (25 if n == 6 else 0) + n * 0.5, video=f"T{person}"))
    for person, depth in ((3, 55), (4, 115)):
        for n in range(1, 9):
            incorrect = n in (6, 8)
            evaluate.append(_rep(person, n, not incorrect, depth - (25 if incorrect else 0) + n * 0.5, video=f"V{person}", split="validation"))
    scored = reference_eval.score_reps(train, evaluate)
    assert len(scored) == 2 * 7  # the reference rep of each person is not scored
    table = {row["view"]: row for row in reference_eval.auc_table(scored) if row["split"] == "validation"}
    assert table["all"]["personal_dtw"] == 1.0
    assert table["all"]["personal_dtw"] > table["all"]["population_peak"]


def test_subject_bootstrap_returns_interval():
    rows = []
    for person in range(1, 6):
        for i in range(6):
            incorrect = int(i >= 4)
            rows.append({"person_id": person, "incorrect": incorrect, "a": incorrect + 0.1 * i, "b": 0.5})
    result = reference_eval.subject_bootstrap(rows, "a", "b", resamples=200)
    assert result["auc_difference"] == pytest.approx(0.5)
    assert result["ci95"][0] <= 0.5 <= result["ci95"][1]
