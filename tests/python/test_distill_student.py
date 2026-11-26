"""Tests for ml/pain/distill_student.py: soft targets, leak removal, score-file checks and threshold matching."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml" / "pain"))
d = pytest.importorskip("distill_student", exc_type=ImportError)


def rows():
    return [{"id": i, "file": "Bone_Diseases", "diagnosis": "", "kind": "ordinary", "title": f"عنوان {i}"} for i in range(1, 60)]


def test_soft_targets_of_zero_and_one_give_the_hard_label_model():
    pytest.importorskip("sklearn")
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(0)
    x = rng.normal(size=(80, 5))
    y = (x[:, 0] + rng.normal(size=80) > 0).astype(float)
    w = rng.uniform(0.5, 2, 80)
    b, coef = d.soft_fit(x, y, w)
    hard = LogisticRegression(C=d.C, max_iter=3000).fit(x, y, sample_weight=w)
    assert abs(b - hard.intercept_[0]) < 1e-4 and np.allclose(coef, hard.coef_[0], atol=1e-4)


def test_a_blind_title_is_removed_even_under_another_number_and_spelling():
    r = rows()
    r[10]["title"] = "ألم  في الصدر"
    blind = [{"id": 31, "title": "الم في الصدر"}]  # same text after normalising; a different consultation number
    kept = d.distillation_titles(r, blind)
    ids = {x["id"] for x in kept}
    assert 11 not in ids and 31 not in ids and not ids & {10, 20, 30, 40, 50}


def test_a_score_file_missing_a_title_raises(tmp_path):
    path = tmp_path / "s.csv"
    path.write_text("kind,key,marbert,camelbert\n" + "".join(f"title,{i},0.1,0.2\n" for i in range(1, 59)), encoding="utf-8")
    with pytest.raises(ValueError, match="1 missing"):
        d.read_scores(path, rows(), {})


def test_threshold_flags_no_more_than_the_target_rate():
    s = np.arange(100) / 100
    t = d.threshold_matching(s, 0.15)
    assert (s > t).mean() <= 0.15 and (s >= t).mean() > 0.15
