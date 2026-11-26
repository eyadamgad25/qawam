"""Tests for ml/eval/keraal_compare.py: labels, scoring, and models on clearly separable data."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("keraal_compare", EVAL_DIR / "keraal_compare.py")
kc = importlib.util.module_from_spec(spec)
sys.modules["keraal_compare"] = kc
spec.loader.exec_module(kc)
FRAMES = kc.km.FRAMES


def test_labels_map_to_the_same_four_classes():
    assert [kc.class_of_group3(x) for x in ("C", "E1B2", "E2B1", "E3B3")] == [0, 1, 2, 3]
    assert kc.class_of_clinician("Correct", None) == 0
    assert kc.class_of_clinician("Incorrect", "Error2") == 2
    assert kc.class_of_clinician("Incomplete", None) is None
    assert kc.class_of_clinician("Incorrect", "Other") is None


def test_file_names_of_group_3_are_understood():
    match = kc.NAME.match("G3-BP-CTK-P2T3-Unknown-E1B2-14")
    assert (match["exercise"], match["person"], match["label"]) == ("CTK", "P2", "E1B2")


def test_accuracy_alone_cannot_hide_a_model_that_always_says_correct():
    rows = [{"y": 0, "p": [1, 0, 0, 0]} for _ in range(9)] + [{"y": 2, "p": [1, 0, 0, 0]}]
    s = kc.scores(rows, "p", "y")
    assert s["accuracy"] == s["majority"] == 0.9
    assert s["balanced"] == 0.5 and s["macro_f1"] < 0.5


def test_threshold_is_the_lowest_confidence_that_stays_within_the_bound():
    clean = [(0.9, False)] * 40 + [(0.6, True)] * 20
    assert kc.confidence_threshold(clean) == 0.9
    assert kc.confidence_threshold([(0.9, i % 2 == 0) for i in range(40)]) is None


def test_aspect_correction_changes_only_the_sideways_scale(tmp_path):
    import json

    frame = {j: [0.5 + 0.1 * (i % 3 - 1), 0.2 + 0.05 * i, 0] for i, j in enumerate(kc.ke.JOINTS)}
    pose = tmp_path / "x.json"
    pose.write_text(json.dumps({"positions": {f"{i}.0": frame for i in range(20)}}))
    plain, wide = kc.ke.features(pose, 1.0, 1), kc.ke.features(pose, 2.0, 1)
    assert not np.allclose(plain, wide) and len(plain) == len(wide) == 20


def _rows(rng, n=12, person="P1"):
    rows = []
    for i in range(n):
        y = i % 4
        wave = np.sin(np.linspace(0, 6, FRAMES) * (y + 1))[:, None]
        x = rng.normal(0, 0.05, (FRAMES, 23)) + wave
        x[:, 3 * y : 3 * y + 3] += 1.5  # the waves alone share mean, spread and range, which is all `linear` sees
        rows.append({"exercise": "CTK", "person": person, "y": y, "input": x})
    return rows


@pytest.mark.parametrize("name", ["knn_dtw", "linear"])
def test_simple_models_learn_clear_classes(name):
    rng = np.random.default_rng(0)
    train, test = _rows(rng, 24), _rows(rng, 12, "P2")
    kc.predict_by_exercise(name, train, test, "p", 1, 1.0)
    assert kc.scores(test, "p", "y")["accuracy"] > 0.9


@pytest.mark.parametrize("name", ["cnn", "gru"])
def test_neural_models_learn_clear_classes(name):
    pytest.importorskip("torch")
    rng = np.random.default_rng(0)
    train, test = _rows(rng, 24), _rows(rng, 12, "P2")
    kc.predict_by_exercise(name, train, test, "p", 1, 1.0)
    assert kc.scores(test, "p", "y")["accuracy"] > 0.9
