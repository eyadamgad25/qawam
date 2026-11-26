"""Tests for ml/eval/keraal_model.py: scoring rules without PyTorch, end to end with it."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("keraal_model", EVAL_DIR / "keraal_model.py")
km = importlib.util.module_from_spec(spec)
sys.modules["keraal_model"] = km
spec.loader.exec_module(km)


def _row(exercise, label, p, person="R1", dtw=None):
    return {"exercise": exercise, "label": label, "p_model": p, "dtw_healthy": dtw, "person": person}


def test_within_exercise_auc_is_not_fooled_by_different_error_rates():
    # the score only knows the exercise: pooled it would look good, within exercise it is chance
    rows = [_row("ELK", i < 8, 0.9) for i in range(10)] + [_row("RTK", i < 2, 0.1) for i in range(10)]
    for r in rows:
        r["label"] = int(r["label"])
    result = km.within_exercise_auc(rows, "p_model", "label")
    assert result["ELK"] == 0.5 and result["RTK"] == 0.5 and result["mean"] == 0.5


def test_recordings_the_clinicians_disagree_on_are_not_training_labels():
    assert km.agreed_label({"verdict_A": "Correct", "verdict_B": "Correct"}) == 0
    assert km.agreed_label({"verdict_A": "Incorrect", "verdict_B": "Incomplete"}) == 1
    assert km.agreed_label({"verdict_A": "Correct", "verdict_B": "Incorrect"}) is None


def test_class_weights_balance_within_each_exercise():
    y = np.array([1, 1, 1, 0, 0, 0, 0, 1], dtype=np.float32)
    ex = ["ELK", "ELK", "ELK", "ELK", "RTK", "RTK", "RTK", "RTK"]
    w = km.balanced_weights(y, ex)
    assert w[:3].sum() == pytest.approx(w[3]) and w[4:7].sum() == pytest.approx(w[7])


def test_majority_baseline_counts_the_minority_of_each_exercise():
    rows = [_row("ELK", 1, 0.5) for _ in range(8)] + [_row("ELK", 0, 0.5) for _ in range(2)] + [_row("RTK", 0, 0.5)]
    assert km.majority_wrong(rows, "label") == (2, 11)


def test_threshold_abstains_when_no_set_is_clean_enough():
    noisy = [_row("CTK", i % 2, 0.9) for i in range(40)]
    assert km.pick_threshold(noisy, "label") is None
    clean = [_row("CTK", 1, 0.95) for _ in range(40)] + [_row("CTK", 1, 0.2) for _ in range(5)]
    assert km.pick_threshold(clean, "label") == pytest.approx(0.45)


def test_model_learns_a_clear_difference_and_never_sees_the_held_out_patient():
    pytest.importorskip("torch")
    rng = np.random.default_rng(0)

    def rec(person, label):
        x = rng.normal(0, 0.05, (km.FRAMES, 23)) + (1.5 if label else 0.0) * np.sin(np.linspace(0, 6, km.FRAMES))[:, None]
        return {"person": person, "exercise": "CTK", "label": label, "input": x}

    rows = [rec(p, i % 2) for p in ("R1", "R2", "R3") for i in range(12)]
    km.out_of_fold(rows, [], seeds=1, epochs=25)
    assert km.within_exercise_auc(rows, "p_model", "label")["mean"] > 0.9
    assert km.count_parameters() < 10000
