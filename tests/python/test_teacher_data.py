"""Tests for ml/pain/teacher_data.py: the training labels shared by the phone model and the Kaggle teachers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml" / "pain"))
import teacher_data as t  # noqa: E402


def rows():
    out = []
    for i in range(1, 400):
        kind = "symptom" if i % 3 == 0 else ("other" if i % 7 == 0 else "ordinary")
        out.append({"id": i, "file": "Bone_Diseases" if kind != "other" else "Internal", "diagnosis": "", "kind": kind, "title": f"t{i}"})
    return out


def test_only_even_training_titles_and_balanced_weights():
    notes = [{"text": f"n{i}", "red_flag": i % 4 == 0} for i in range(20)]
    texts, y, w = t.training_set(rows(), notes, others=5)
    real = len(y) - len(notes)
    used = {int(x[1:]) for x in texts[:real]}
    assert all(i % 2 == 0 and i % 10 for i in used)
    assert texts[real:] == [n["text"] for n in notes]
    for block in (slice(0, real), slice(real, None)):
        for c in (0, 1):
            assert abs(w[block][y[block] == c].sum() - len(y) / 4) < 1e-9


def test_held_out_titles_are_the_even_ones_ending_in_zero():
    fit, held = t.fit_rows(rows())
    assert all(r["id"] % 10 == 0 for r in held) and not {r["id"] for r in fit} & {r["id"] for r in held}
