"""Tests for ml/eval/fit3d_extract.py on a tiny fake Fit3D archive."""

import importlib.util
import json
import sys
import tarfile
from pathlib import Path

import numpy as np
import pytest

EVAL_DIR = Path(__file__).resolve().parents[2] / "ml" / "eval"
sys.path.insert(0, str(EVAL_DIR))
spec = importlib.util.spec_from_file_location("fit3d_extract", EVAL_DIR / "fit3d_extract.py")
fit3d_extract = importlib.util.module_from_spec(spec)
sys.modules["fit3d_extract"] = fit3d_extract
spec.loader.exec_module(fit3d_extract)


def test_only_needed_members_for_pack_exercises_are_unpacked():
    assert fit3d_extract.wanted("fit3d/train/s03/videos/50591643/squat.mp4")
    assert fit3d_extract.wanted("fit3d/train/s03/joints3d_25/dumbbell_reverse_lunge.json")
    assert not fit3d_extract.wanted("fit3d/train/s03/videos/50591643/pushup.mp4")
    assert not fit3d_extract.wanted("fit3d/train/s03/smplx/squat.json")


def test_projection_without_distortion_is_the_pinhole_model():
    intr = {"f": [[1000.0, 1000.0]], "c": [[500.0, 400.0]], "k": [[0.0, 0.0, 0.0]], "p": [[0.0, 0.0]]}
    out = fit3d_extract.project(np.array([[0.1, -0.2, 2.0]]), intr)
    assert np.allclose(out, [[550.0, 300.0]])


def test_archive_to_npz_end_to_end(tmp_path):
    cv2 = pytest.importorskip("cv2")
    pytest.importorskip("mediapipe")
    if not fit3d_extract.DEFAULT_MODEL.exists():
        pytest.skip("pose model not on this machine (data/ is git-ignored)")
    root = tmp_path / "src" / "fit3d" / "train" / "s03"
    for sub in ("videos/cam1", "joints3d_25", "camera_parameters/cam1", "smplx"):
        (root / sub).mkdir(parents=True)
    writer = cv2.VideoWriter(str(root / "videos/cam1/squat.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 50, (64, 64))
    for _ in range(9):
        writer.write(np.zeros((64, 64, 3), np.uint8))
    writer.release()
    joints = np.tile(np.linspace(0.1, 1.0, 25)[:, None] * [1, 1, 0] + [0, 0, 3], (9, 1, 1))
    (root / "joints3d_25/squat.json").write_text(json.dumps({"joints3d_25": joints.tolist()}))
    intr = {"f": [[100.0, 100.0]], "c": [[32.0, 32.0]], "k": [[0.0, 0.0, 0.0]], "p": [[0.0, 0.0]]}
    params = {"extrinsics": {"R": np.eye(3).tolist(), "T": [[0.0, 0.0, 0.0]]}, "intrinsics_w_distortion": intr}
    (root / "camera_parameters/cam1/squat.json").write_text(json.dumps(params))
    (root / "smplx/squat.json").write_text("{}")
    archive = tmp_path / "fit3d_train.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(tmp_path / "src" / "fit3d", arcname="fit3d")
    out = tmp_path / "out"
    assert fit3d_extract.main(["--archive", str(archive), "--work", str(tmp_path / "work"), "--out", str(out)]) == 0
    assert not list((tmp_path / "work").rglob("smplx"))  # unneeded parts stay packed
    data = np.load(out / "s03_squat_cam1.npz")
    assert data["frames"].tolist() == [0, 3, 6]
    assert data["marks"].shape == (3, 33, 5) and np.isnan(data["marks"]).all()  # blank video: no pose
    assert data["gt3d"].shape == (3, 25, 3)
    assert np.allclose(data["gt2d"][0, 24], [32 + 100 * 1.0 / 3, 32 + 100 * 1.0 / 3], atol=1e-3)
    assert json.loads(str(data["meta"]))["action"] == "squat"
