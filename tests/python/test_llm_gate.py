"""Tests for ml/pain/llm_gate.py and the LLM-label mode of teacher_data.training_set."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml" / "pain"))
import llm_gate as g  # noqa: E402
import teacher_data as t  # noqa: E402


def test_kappa_known_cases():
    assert g.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0
    assert abs(g.cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0])) < 1e-12
    assert g.cohen_kappa([1, 1, 0, 0], [0, 0, 1, 1]) == -1.0


def test_threshold_maximises_macro_f1():
    p = [0.9, 0.8, 0.6, 0.4, 0.2, 0.1]
    y = [1, 1, 1, 0, 0, 0]
    assert g.best_threshold(p, y) == 0.6


def rows():
    return [{"id": i, "file": "Bone_Diseases" if i % 7 else "Internal", "diagnosis": "", "title": f"t{i}",
             "kind": "symptom" if i % 3 == 0 else ("other" if i % 7 == 0 else "ordinary")} for i in range(1, 400)]


def test_llm_labels_replace_category_labels_and_a_missing_one_raises():
    pos, neg = t.training_rows(rows(), others=5)
    labels = {r["id"]: 0 for r in pos} | {r["id"]: 1 for r in neg}
    _, y, _ = t.training_set(rows(), [], others=5, labels=labels)
    assert y.tolist() == [0] * len(pos) + [1] * len(neg)
    del labels[neg[0]["id"]]
    with pytest.raises(ValueError, match="1 training titles"):
        t.training_set(rows(), [], others=5, labels=labels)
