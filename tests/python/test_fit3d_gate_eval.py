"""Tests for ml/eval/fit3d_gate_eval.py on synthetic Fit3D-style .npz files."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("fit3d_gate_eval", EVAL_DIR / "fit3d_gate_eval.py")
fit3d = importlib.util.module_from_spec(spec)
sys.modules["fit3d_gate_eval"] = fit3d
spec.loader.exec_module(fit3d)

H36M = fit3d.H36M_FOR_LANDMARK
MP = fit3d.MEDIAPIPE_INDEX


def _squat(view: str, reps: int = 5, per_rep: int = 30, seed: int = 0):
    """Knee bending to 90 deg flexion in 3D. Side view keeps the angle in the image; front view squashes it."""
    rng = np.random.default_rng(seed)
    gt, gt3, marks = [], [], []
    for t in np.tile(np.sin(np.linspace(0, np.pi, per_rep)), reps):
        bend = np.radians(90 * t)
        g = np.zeros((25, 2))
        for hip, knee, ankle, shoulder, dx in ((4, 5, 6, 11, -1), (1, 2, 3, 14, 1)):
            ankle_xy = np.array([500 + dx * (40 if view == "front" else 3), 900])
            knee_xy = ankle_xy + [0, -200]
            # side view: thigh rotates in the image plane; front view: it points at the camera
            thigh = [200 * np.sin(bend), -200 * np.cos(bend)] if view == "side" else [0, -200 * np.cos(bend)]
            hip_xy = knee_xy + thigh
            g[ankle], g[knee], g[hip] = ankle_xy, knee_xy, hip_xy
            g[shoulder] = hip_xy + [dx * (60 if view == "front" else 4), -300]
        w = np.zeros((25, 3))
        for hip, knee, ankle, shoulder, dz in ((4, 5, 6, 11, -0.1), (1, 2, 3, 14, 0.1)):
            w[ankle], w[knee] = [0, 0, dz], [0, 0.4, dz]
            w[hip] = w[knee] + [0.4 * np.sin(bend), 0.4 * np.cos(bend), 0]
            w[shoulder] = w[hip] + [0, 0.6, 0]
        m = np.full((33, 5), np.nan)
        for name, index in MP.items():
            if name in H36M:
                m[index, :2] = g[H36M[name]] + rng.normal(0, 1.5, 2) + [3, 0]
        m[:, 2], m[:, 3], m[:, 4] = 0.0, 0.95, 0.99
        m = np.nan_to_num(m, nan=0.0)
        gt.append(g)
        gt3.append(w)
        marks.append(m)
    return np.array(gt), np.array(gt3), np.array(marks)


def _write(folder: Path, subject: str, camera: str, view: str, seed: int):
    gt2d, gt3d, marks = _squat(view, seed=seed)
    meta = {"subject": subject, "action": "squat", "camera": camera, "fps": 50, "width": 1000, "height": 1000}
    np.savez_compressed(folder / f"{subject}_squat_{camera}.npz", frames=np.arange(len(gt2d)), marks=marks,
                        gt2d=gt2d, gt3d=gt3d, meta=json.dumps(meta))


def test_action_names_map_to_packs():
    assert fit3d.pack_for_action("squat") == "lower-limb.squat"
    assert fit3d.pack_for_action("dumbbell_reverse_lunge") == "lower-limb.lunge"
    assert fit3d.pack_for_action("side_lateral_raise") == "upper-limb.shoulder-abduction"
    assert fit3d.pack_for_action("pushup") is None


def test_shipped_rule_speaks_side_on_and_refuses_front_view(tmp_path):
    for i, subject in enumerate(("s03", "s04", "s05", "s07")):
        _write(tmp_path, subject, "side_cam", "side", seed=i)
        _write(tmp_path, subject, "front_cam", "front", seed=10 + i)
    out = tmp_path / "out"
    assert fit3d.main(["--features", str(tmp_path), "--out", str(out)]) == 0
    report = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert report["gt_left_right_mirrored"] is False
    cams = report["shipped_rule"]["by_camera"]
    assert cams["side_cam"]["coverage"] > 0.9 and cams["side_cam"]["false_cue_rate"] == 0.0
    assert cams["front_cam"]["coverage"] == 0.0
    assert cams["front_cam"]["always_speak_risk"] == 1.0  # the squashed front-view angle is wrong, so refusing is right
    assert "learned_gate" in report
    assert "Shipped view rule" in (out / "summary.md").read_text(encoding="utf-8")
