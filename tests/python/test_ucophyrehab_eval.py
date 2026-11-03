"""Tests for ml/eval/ucophyrehab_eval.py on a tiny synthetic UCOPhyRehab++-style folder."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("ucophyrehab_eval", EVAL_DIR / "ucophyrehab_eval.py")
ucophyrehab_eval = importlib.util.module_from_spec(spec)
sys.modules["ucophyrehab_eval"] = ucophyrehab_eval
spec.loader.exec_module(ucophyrehab_eval)

FRAMES_PER_REP = 40


def _write_dataset(root: Path, people: dict[str, list[float]]) -> None:
    """Knee extension from 90 deg; each rep reaches 90 + depth; score falls with lost range."""
    meta, records = [], []
    for subject, depths in people.items():
        frames, scores, frame_id = [], [], 5
        best = max(depths)
        for depth in depths:
            start = frame_id
            for t in np.linspace(0, np.pi, FRAMES_PER_REP):
                angle = 90 + np.sin(t) * depth
                frames.append({"id": frame_id, "joints": {"l_hip": {}, "l_knee": {}, "l_ankle": {}, "angle": angle}})
                frame_id += 1
            scores.append({"init_frame": start, "final_frame": frame_id - 1,
                           "score": 5.0 if depth == best else (4.0 if depth > best - 30 else 3.0)})
        frames.append({"id": frame_id, "joints": None})  # a dropped frame must not break loading
        meta.append({"subject_id": subject, "exercise_id": "01", "scores": scores})
        records.append({"folder": subject, "exercise": "01", "position": "seated", "side": "left",
                        "body": "lower", "frames": frames})
    records.append({"folder": "empty", "exercise": "01", "frames": None, "body": "lower"})
    (root / "ucophyrehab2_data.jsonl").write_text("\n".join(json.dumps(m) for m in meta), encoding="utf-8")
    (root / "dataset_3d_with_angles.json").write_text(json.dumps({"data": records}), encoding="utf-8")


def test_spearman_handles_ties():
    assert ucophyrehab_eval.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert round(ucophyrehab_eval.spearman([1, 1, 2, 3], [1, 2, 3, 4]), 3) == 0.949
    assert ucophyrehab_eval.spearman([1, 1, 1], [1, 2, 3]) is None


def test_rep_curve_rejects_mostly_missing_reps():
    series = {i: float(i) for i in range(0, 10)}
    assert ucophyrehab_eval.rep_curve(series, 0, 9).tolist() == list(map(float, range(10)))
    assert ucophyrehab_eval.rep_curve({0: 0.0, 9: 9.0}, 0, 9) is None


def test_personal_reference_tracks_score_and_counter_counts_reps(tmp_path):
    people = {
        "A": [80, 80, 75, 40, 80, 45],
        "B": [70, 70, 30, 70, 35, 65],
        "C": [85, 85, 50, 85, 80, 45],
    }
    _write_dataset(tmp_path, people)
    out = tmp_path / "out"
    assert ucophyrehab_eval.main(["--root", str(tmp_path), "--out", str(out)]) == 0
    report = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    personal = next(r for r in report["agreement"]["all"] if r["method"] == "personal_best")
    assert personal["rho"] > 0.8 and personal["auc_low"] == 1.0
    assert report["counting"]["exact"] == 1.0
    assert "rho" in (out / "summary.md").read_text(encoding="utf-8")
