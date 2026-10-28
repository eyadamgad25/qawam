"""Tests for ml/eval/angle_eval.py with a synthetic dataset and a fake landmarker."""

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from qawam_ml.packs import MEDIAPIPE_INDEX, REHAB24_JOINT_FOR_LANDMARK, load_packs
from qawam_ml.rehab24 import CSV_COLUMNS, SealedTestSplitError

EVAL_PATH = Path(__file__).resolve().parents[2] / "ml" / "eval" / "angle_eval.py"
spec = importlib.util.spec_from_file_location("angle_eval", EVAL_PATH)
angle_eval = importlib.util.module_from_spec(spec)
sys.modules["angle_eval"] = angle_eval
spec.loader.exec_module(angle_eval)

cv2 = pytest.importorskip("cv2")

WIDTH, HEIGHT, N_FRAMES = 320, 480, 40


def _skeleton(frame: int) -> np.ndarray:
    """26-joint 2D skeleton doing a squat: knees bend and straighten."""
    joints = np.zeros((26, 2))
    bend = np.sin(np.pi * frame / (N_FRAMES - 1))
    for side, dx in (("LEFT", -20.0), ("RIGHT", 20.0)):
        hip = np.array([160 + dx, 200 + 60 * bend])
        knee = hip + np.array([40 * bend, 100 - 30 * bend])
        ankle = np.array([160 + dx, 400])
        shoulder = np.array([160 + dx, 80 + 50 * bend])
        for name, point in (("HIP", hip), ("KNEE", knee), ("ANKLE", ankle), ("SHOULDER", shoulder)):
            joints[REHAB24_JOINT_FOR_LANDMARK[f"{side}_{name}"]] = point
    for name in ("ELBOW", "WRIST"):
        for side in ("LEFT", "RIGHT"):
            joints[REHAB24_JOINT_FOR_LANDMARK[f"{side}_{name}"]] = (160, 150)
    return joints


@pytest.fixture()
def dataset(tmp_path):
    root = tmp_path / "rehab24-6"
    folder = root / "Ex6"
    folder.mkdir(parents=True)
    joints = np.stack([_skeleton(f) for f in range(N_FRAMES)])
    rows = []
    for video_id, person in (("PM_900", 8), ("PM_901", 4), ("PM_902", 7)):
        for cam, name in ((17, f"{video_id}-Camera17-30fps.mp4"), (18, f"{video_id}-Camera18-30fps-transposed.mp4")):
            writer = cv2.VideoWriter(str(folder / name), cv2.VideoWriter_fourcc(*"mp4v"), 30, (WIDTH, HEIGHT))
            for _ in range(N_FRAMES):
                writer.write(np.full((HEIGHT, WIDTH, 3), 128, np.uint8))
            writer.release()
            np.save(folder / f"{video_id}-c{cam}-30fps.npy", joints)
        rows.append([video_id, 1, 6, person, 0, N_FRAMES - 1, "front", 0, "", 1, 0, 0, 1])
    with (root / "Segmentation.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(CSV_COLUMNS)
        writer.writerows(rows)
    splits = tmp_path / "splits.json"
    splits.write_text(json.dumps({"train": [8], "validation": [4], "test": [7]}))
    return root, splits, joints


class _FakeLandmarker:
    """Returns the ground-truth skeleton as normalised landmarks; bias shifts the knees."""

    def __init__(self, joints, bias_px=0.0):
        self.joints, self.bias = joints, bias_px

    def detect_for_video(self, image, timestamp_ms):
        frame = round(timestamp_ms * 30 / 1000)
        marks = [SimpleNamespace(x=0.5, y=0.5, visibility=0.9) for _ in range(33)]
        for name, index in MEDIAPIPE_INDEX.items():
            if name in REHAB24_JOINT_FOR_LANDMARK:
                x, y = self.joints[frame, REHAB24_JOINT_FOR_LANDMARK[name]]
                shift = self.bias if name.endswith("KNEE") else 0.0
                marks[index] = SimpleNamespace(x=(x + shift) / WIDTH, y=y / HEIGHT, visibility=0.95)
        return SimpleNamespace(pose_landmarks=[marks])

    def close(self):
        pass


def _patch(monkeypatch, dataset, bias=0.0):
    root, splits, joints = dataset
    fake_mp = SimpleNamespace(Image=lambda image_format, data: data, ImageFormat=SimpleNamespace(SRGB=1))
    monkeypatch.setattr(angle_eval, "_landmarker", lambda model: (fake_mp, _FakeLandmarker(joints, bias)))
    import qawam_ml.rehab24 as rehab24

    original = rehab24.load_repetitions

    def load(split, **kwargs):
        return original(split, splits_path=splits, test_access_log=root / "access.jsonl", **kwargs)

    monkeypatch.setattr(angle_eval, "load_repetitions", load)
    return root


def test_sides_and_frames():
    packs = load_packs()
    squat = angle_eval.pack_for_exercise(packs, 6)
    lunge = angle_eval.pack_for_exercise(packs, 5)
    assert angle_eval.sides_for_rep(squat, "") == ["left", "right"]
    assert angle_eval.sides_for_rep(lunge, "front leg right") == ["right"]
    rep = SimpleNamespace(first_frame=3, last_frame=5)
    assert sorted(angle_eval.needed_frames([rep], 5)) == [3, 4]


def test_perfect_pose_gives_zero_error(monkeypatch, dataset, tmp_path):
    root = _patch(monkeypatch, dataset)
    model = tmp_path / "model.task"
    model.write_bytes(b"x")
    out = tmp_path / "out"
    assert angle_eval.main(["--dataset-root", str(root), "--model", str(model), "--out", str(out)]) == 0
    summary = json.loads((out / "summary.json").read_text())
    assert all(row["mae_deg"] == 0.0 for row in summary["error_by_view"])
    assert {row["split"] for row in summary["error_by_view"]} == {"train", "validation"}
    reps = list(csv.DictReader((out / "reps.csv").open()))
    assert len(reps) == 2 * 2 * 2  # 2 splits x 2 cameras x 2 sides
    assert all(r["wrong"] == "0" for r in reps)


def test_biased_pose_produces_error(monkeypatch, dataset, tmp_path):
    root = _patch(monkeypatch, dataset, bias=25.0)
    model = tmp_path / "model.task"
    model.write_bytes(b"x")
    out = tmp_path / "out"
    angle_eval.main(["--dataset-root", str(root), "--model", str(model), "--out", str(out), "--cameras", "17"])
    summary = json.loads((out / "summary.json").read_text())
    assert all(row["mae_deg"] > 1.0 for row in summary["error_by_view"])


def test_test_split_stays_sealed(monkeypatch, dataset, tmp_path):
    root = _patch(monkeypatch, dataset)
    model = tmp_path / "model.task"
    model.write_bytes(b"x")
    with pytest.raises(SealedTestSplitError):
        angle_eval.main(["--dataset-root", str(root), "--model", str(model), "--out", str(tmp_path / "o"), "--splits", "test"])
    assert not (root / "access.jsonl").exists()
