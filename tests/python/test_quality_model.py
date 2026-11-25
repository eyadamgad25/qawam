"""Tests for ml/eval/quality_model.py: features, references, person-wise splits and the 'not sure' rule."""

import importlib.util
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("quality_model", EVAL_DIR / "quality_model.py")
q = importlib.util.module_from_spec(spec)
sys.modules["quality_model"] = q
spec.loader.exec_module(q)


def body(frames=30, depth=1.0, lean=0.0):
    """A stick figure squatting: the knees move out and the hips drop, scaled by depth; the trunk leans."""
    s = np.sin(np.linspace(0, np.pi, frames)) * depth
    pts = np.zeros((frames, 13, 2))
    for side, x in (("LEFT", -0.2), ("RIGHT", 0.2)):
        pts[:, q.P[f"{side}_ANKLE"]] = (x, 2.0)
        pts[:, q.P[f"{side}_KNEE"]] = np.stack([x + 0.4 * s, 1.5 + 0 * s], 1)
        pts[:, q.P[f"{side}_HIP"]] = np.stack([x + 0 * s, 1.0 + 0.4 * s], 1)
        pts[:, q.P[f"{side}_SHOULDER"]] = np.stack([x + lean * s, 0.4 * s], 1)
        pts[:, q.P[f"{side}_ELBOW"]] = pts[:, q.P[f"{side}_SHOULDER"]] + (0, 0.5)
        pts[:, q.P[f"{side}_WRIST"]] = pts[:, q.P[f"{side}_SHOULDER"]] + (0.1, 0.9)
    pts[:, q.P["HEAD"]] = np.stack([lean * s, 0.4 * s - 0.4], 1)
    return pts


def rep(person, i, incorrect=0, scale=1.0, shift=(0.0, 0.0), rng=None, depth=1.0, lean=0.0):
    pts = body(depth=depth, lean=lean)
    if rng is not None:
        pts = pts + rng.normal(0, 0.01, pts.shape)
    return q.make_rep(pts * scale + shift, 30.0, dataset="t", person=person, exercise="squat", group=(person,), order=(i,),
                      incorrect=incorrect, view="side")


def people(n=5, rng_seed=0):
    rng = np.random.default_rng(rng_seed)
    reps = []
    for p in range(n):
        own = 0.7 + 0.15 * p  # every person has their own correct depth
        for i in range(14):
            bad = int(i >= 4 and i % 2)
            reps.append(rep(f"P{p}", i, bad, rng=rng, depth=own * (0.6 if bad else 1), lean=0.1))
    return reps


def test_features_ignore_distance_to_the_camera_and_position_in_the_image():
    assert np.allclose(rep("A", 0).channels, rep("A", 0, scale=250.0, shift=(900, 400)).channels, atol=1e-3)


def test_a_rep_compared_with_itself_has_no_difference():
    gap, feats, dist = q.compare(rep("A", 0), rep("A", 1))
    assert np.allclose(gap, 0) and np.allclose(feats, 0) and dist == 0


def test_alignment_forgives_speed_but_not_depth():
    slow = rep("A", 0)
    t = np.linspace(0, 1, q.LENGTH) ** 1.5
    fast = q.Rep(**{**slow.__dict__, "channels": np.stack(
        [np.interp(t, np.linspace(0, 1, q.LENGTH), slow.channels[:, c]) for c in range(slow.channels.shape[1])], 1)})
    assert q.compare(fast, slow)[2] < 0.3 * q.compare(rep("A", 1, depth=0.6), slow)[2]


def test_reference_reps_are_the_first_correct_ones_and_never_scored():
    reps = [rep("A", i, incorrect=int(i == 0)) for i in range(6)]
    rows = q.personalise(reps, 3)
    assert sorted(r["rep"].order[0] for r in rows) == [0, 4, 5]
    assert q.personalise(reps[:3], 3) == []


def test_model_beats_a_single_cut_off_when_people_differ_and_never_trains_on_the_person_it_scores(monkeypatch):
    rows = q.personalise(people(), 3)
    seen = []
    real = q.fit_logistic
    monkeypatch.setattr(q, "fit_logistic", lambda x, y, s: seen.append(len(y)) or real(x, y, s))
    q.leave_one_person_out(rows)
    per_person = len(rows) // 5
    assert seen == [len(rows) - per_person] * 5
    assert q.evaluate(rows, "model", "p_model")["macro_f1"] > 0.9


def test_majority_answer_cannot_look_good():
    rows = [{"y": int(i < 2), "says": False, "person": str(i % 4), "exercise": "e"} for i in range(20)]
    s = q.evaluate(rows, "says", None)
    assert s["accuracy"] == s["majority"] == 0.9 and s["macro_f1"] < 0.5 and s["f1"] == 0


def test_not_sure_stays_silent_when_the_model_guesses():
    rng = np.random.default_rng(1)
    rows = [{"y": int(rng.integers(2)), "person": str(i % 6), "p_model": float(rng.random())} for i in range(120)]
    for r in rows:
        r["model"] = r["p_model"] >= 0.5
    assert q.abstention(rows)["answered"] <= 12


def test_weights_balance_classes_inside_each_exercise():
    x = np.array([[0.0], [0.0], [0.0], [1.0]])
    model = q.fit_logistic(x, np.array([0, 0, 0, 1]), np.array(["a"] * 4))
    p = q.predict_logistic(model, x)
    assert p[0] < 0.5 < p[3] and abs(p[0] + p[3] - 1) < 0.05


def test_transfer_uses_cut_offs_from_the_training_set_only():
    train, test = q.personalise(people(rng_seed=1), 3), q.personalise(people(rng_seed=2), 3)
    q.transfer(train, test)
    before = [r["dtw_z_says"] for r in test]
    for r in test:
        r["y"] = 1 - r["y"]  # test labels must not change any decision
    q.transfer(train, test)
    assert before == [r["dtw_z_says"] for r in test]
    assert {"model", "dtw_says", "dtw_z_says"} <= set(test[0])
