"""Tests for ml/eval/rehab26_eval.py on a tiny synthetic REHAB26-style folder."""

import importlib.util
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("rehab26_eval", EVAL_DIR / "rehab26_eval.py")
rehab26_eval = importlib.util.module_from_spec(spec)
sys.modules["rehab26_eval"] = rehab26_eval
spec.loader.exec_module(rehab26_eval)

HEADER = "video_id;exercise_id;exercise_subtype;person;repetition_number;first_frame;last_frame;person_orientation;correctness_score;error_description;additional_errors\n"


def test_viewing_angles_follow_dataset_definition():
    assert rehab26_eval.viewing_angle(0, 1) == 0
    assert rehab26_eval.viewing_angle(0, 3) == 90
    assert rehab26_eval.viewing_angle(45, 2) == 0
    assert rehab26_eval.view_bucket(-90) == "profile 80-90"
    assert rehab26_eval.view_bucket(30) == "oblique 20-35"


def _squat_frames(depths, frames_per_rep=30):
    """33-landmark normalised skeleton squatting to the given knee depths in turn."""
    out = []
    for depth in depths:
        for t in np.linspace(0, np.pi, frames_per_rep):
            bend = np.sin(t) * depth / 100
            marks = np.zeros((33, 4))
            marks[:, 3] = 0.95
            for hip, knee, ankle, shoulder, dx in ((23, 25, 27, 11, -0.02), (24, 26, 28, 12, 0.02)):
                marks[hip, :2] = (0.5 + dx, 0.45 + 0.1 * bend)
                marks[knee, :2] = (0.5 + dx + 0.08 * bend, 0.65)
                marks[ankle, :2] = (0.5 + dx, 0.85)
                marks[shoulder, :2] = (0.5 + dx, 0.25 + 0.08 * bend)
            out.append(marks)
    return np.stack(out)


def test_personal_reference_runs_end_to_end(tmp_path):
    root = tmp_path / "rehab26"
    folder = root / "mp" / "mediapipe" / "ex6"
    folder.mkdir(parents=True)
    lines = [HEADER]
    for p_index, (person, depth) in enumerate((("A", 60), ("B", 100), ("C", 80))):
        depths = [depth, depth, depth, depth - 35, depth, depth - 35]
        frames = _squat_frames(depths)
        for cam in (1, 2, 3):
            np.save(folder / f"ex6_{person}_cam{cam}_2d.npy", frames)
        for r, d in enumerate(depths):
            bad = d != depth
            lines.append(f"ex6_{person};6;;{person};{r + 1};{r * 30};{r * 30 + 29};0;{5 if bad else 1};{'ERR_SHALLOW_SQUAT' if bad else ''};\n")
    (root / "Segmentation.csv").write_text("".join(lines))
    out = tmp_path / "out"
    assert rehab26_eval.main(["--root", str(root), "--exercises", "6", "--out", str(out)]) == 0
    summary = (out / "summary.md").read_text()
    assert "ERR_SHALLOW_SQUAT" in summary
    import json

    data = json.loads((out / "summary.json").read_text())
    overall = next(r for r in data["exercises"]["lower-limb.squat"]["by_view"] if r["view"] == "all")
    assert overall["personal_dtw"] == 1.0
